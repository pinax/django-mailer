import contextlib
import logging
import smtplib
import time
from socket import error as socket_error

import lockfile
from django import VERSION as DJANGO_VERSION
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail import get_connection
from django.core.mail.message import make_msgid
from django.core.mail.utils import DNS_NAME
from django.db import DatabaseError, NotSupportedError, OperationalError, transaction
from django.utils.module_loading import import_string

from mailer.models import RESULT_FAILURE, RESULT_SUCCESS, Message, MessageLog, get_message_id

if DJANGO_VERSION[0] >= 2:
    NotSupportedFeatureException = NotSupportedError
else:
    NotSupportedFeatureException = DatabaseError


# when queue is empty, how long to wait (in seconds) before checking again
EMPTY_QUEUE_SLEEP = getattr(settings, "MAILER_EMPTY_QUEUE_SLEEP", 30)

# lock timeout value. how long to wait for the lock to become available.
# default behavior is to never wait for the lock to be available.
LOCK_WAIT_TIMEOUT = getattr(settings, "MAILER_LOCK_WAIT_TIMEOUT", -1)

# allows for a different lockfile path. The default is a file
# in the current working directory.
LOCK_PATH = getattr(settings, "MAILER_LOCK_PATH", None)

logger = logging.getLogger(__name__)


def prioritize(queryset=None):
    """
    Returns the messages in the queue in the order they should be sent.
    """
    if queryset:
        return queryset.order_by("priority", "when_added")
    return Message.objects.non_deferred().order_by("priority", "when_added")


@contextlib.contextmanager
def sender_context(message):
    """
    Makes a context manager appropriate for sending a message.
    Entering the context using `with` may return a `None` object if the message
    has been sent/deleted already.
    """
    # We wrap each message sending inside a transaction (otherwise
    # select_for_update doesn't work).

    # We also do `nowait` for databases that support it. The result of this is
    # that if two processes (which might be on different machines) both attempt
    # to send the same queue, the loser for the first message will immediately
    # get an error, and will be able to try the second message. This means the
    # work for sending the messages will be distributed between the two
    # processes. Otherwise, the losing process has to wait for the winning
    # process to finish and release the lock, and the winning process will
    # almost always win the next message etc.
    with transaction.atomic():
        try:
            try:
                yield Message.objects.filter(id=message.id).select_for_update(nowait=True).get()
            except NotSupportedFeatureException:
                # MySQL
                yield Message.objects.filter(id=message.id).select_for_update().get()
        except Message.DoesNotExist:
            # Deleted by someone else
            yield None
        except OperationalError:
            # Locked by someone else
            yield None


def get_messages_for_sending(queryset=None):
    """
    Returns a series of context managers that are used for sending mails in the queue.
    Entering the context manager returns the actual message
    """
    for message in prioritize(queryset):
        yield sender_context(message)


def ensure_message_id(msg):
    if get_message_id(msg) is None:
        # Use cached DNS_NAME for performance
        msg.extra_headers["Message-ID"] = make_msgid(domain=DNS_NAME)


def _limits_reached(sent, deferred):
    # Allow sending a fixed/limited amount of emails in each delivery run
    # defaults to None which means send everything in the queue
    EMAIL_MAX_BATCH = getattr(settings, "MAILER_EMAIL_MAX_BATCH", None)

    if EMAIL_MAX_BATCH is not None and sent >= EMAIL_MAX_BATCH:
        logger.info("EMAIL_MAX_BATCH (%s) reached, stopping for this round", EMAIL_MAX_BATCH)
        return True

    # Stop sending emails in the current round if more than X emails get
    # deferred - defaults to None which means keep going regardless
    EMAIL_MAX_DEFERRED = getattr(settings, "MAILER_EMAIL_MAX_DEFERRED", None)

    if EMAIL_MAX_DEFERRED is not None and deferred >= EMAIL_MAX_DEFERRED:
        logger.warning("EMAIL_MAX_DEFERRED (%s) reached, stopping for this round", EMAIL_MAX_DEFERRED)
        return True


def _throttle_emails():
    # When delivering, wait some time between emails to avoid server overload
    # defaults to 0 for no waiting
    EMAIL_THROTTLE = getattr(settings, "MAILER_EMAIL_THROTTLE", 0)

    if EMAIL_THROTTLE:
        logger.debug("Throttling email delivery. Sleeping %s seconds", EMAIL_THROTTLE)
        time.sleep(EMAIL_THROTTLE)


def handle_delivery_exception(connection, message, exc):
    if isinstance(
        exc,
        (
            smtplib.SMTPAuthenticationError,
            smtplib.SMTPDataError,
            smtplib.SMTPRecipientsRefused,
            smtplib.SMTPSenderRefused,
            socket_error,
        ),
    ):
        message.defer()
        logger.info(f"message deferred due to failure: {exc}")
        MessageLog.objects.log(message, RESULT_FAILURE, log_message=str(exc))

        connection = None  # i.e. enforce creation of a new connection
        status = "deferred"

        return connection, status

    # The idea is (1) to be backwards compatible with existing behavior
    # and (2) not have delivery errors go unnoticed
    raise exc


def acquire_lock():
    logger.debug("acquiring lock...")
    if LOCK_PATH is not None:
        lock_file_path = LOCK_PATH
    else:
        lock_file_path = "send_mail"

    lock = lockfile.FileLock(lock_file_path)

    try:
        lock.acquire(LOCK_WAIT_TIMEOUT)
    except lockfile.AlreadyLocked:
        logger.error("lock already in place. quitting.")
        return False, lock
    except lockfile.LockTimeout:
        logger.error("waiting for the lock timed out. quitting.")
        return False, lock
    logger.debug("acquired.")
    return True, lock


def release_lock(lock):
    logger.debug("releasing lock...")
    lock.release()
    logger.debug("released.")


def _require_no_backend_loop(mailer_email_backend):
    if mailer_email_backend == settings.EMAIL_BACKEND == "mailer.backend.DbBackend":
        raise ImproperlyConfigured(
            "EMAIL_BACKEND and MAILER_EMAIL_BACKEND"
            ' should not both be set to "{}"'
            " at the same time".format(settings.EMAIL_BACKEND)
        )


def send_all(queryset=None):
    """
    Send all eligible messages in the queue.
    """
    # The actual backend to use for sending, defaulting to the Django default.
    # To make testing easier this is not stored at module level.
    mailer_email_backend = getattr(settings, "MAILER_EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend")

    # allows disabling file locking. The default is True
    use_file_lock = getattr(settings, "MAILER_USE_FILE_LOCK", True)

    error_handler = import_string(getattr(settings, "MAILER_ERROR_HANDLER", "mailer.engine.handle_delivery_exception"))

    _require_no_backend_loop(mailer_email_backend)

    if use_file_lock:
        acquired, lock = acquire_lock()
        if not acquired:
            return

    start_time = time.time()

    counts = {"deferred": 0, "sent": 0}

    try:
        connection = None
        for context in get_messages_for_sending(queryset):
            with context as message:
                if message is None:
                    # We didn't acquire the lock
                    continue
                try:
                    if connection is None:
                        connection = get_connection(backend=mailer_email_backend)
                    logger.info(f"sending message '{message.subject}' to {', '.join(map(str, message.to_addresses))}")
                    email = message.email
                    if email is not None:
                        email.connection = connection
                        ensure_message_id(email)
                        email.send()

                        # connection can't be stored in the MessageLog
                        email.connection = None
                        message.email = email  # For the sake of MessageLog
                        MessageLog.objects.log(message, RESULT_SUCCESS)
                        counts["sent"] += 1
                    else:
                        logger.warning(
                            f"message discarded due to failure in converting from DB. Added on "
                            f"'{message.when_added}' with priority '{message.priority}'"
                        )  # noqa
                    message.delete()

                except Exception as err:
                    connection, action_taken = error_handler(connection, message, err)
                    counts[action_taken] += 1

            # Check if we reached the limits for the current run
            if _limits_reached(counts["sent"], counts["deferred"]):
                _throttle_emails()
                break

            _throttle_emails()

    finally:
        if use_file_lock:
            release_lock(lock)

    logger.info(
        "Sent",
        extra={
            "sent": counts["sent"],
            "deferred": counts["deferred"],
            "duration": time.time() - start_time,
        },
    )


def send_loop():
    """
    Loop indefinitely, checking queue at intervals of EMPTY_QUEUE_SLEEP and
    sending messages if any are on queue.
    """

    while True:
        while not Message.objects.non_deferred().exists():
            logger.debug(f"sleeping for {EMPTY_QUEUE_SLEEP} seconds before checking queue again")
            time.sleep(EMPTY_QUEUE_SLEEP)
        send_all()
