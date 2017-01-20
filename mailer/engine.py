from __future__ import unicode_literals

import time
import smtplib
import logging

import lockfile
from socket import error as socket_error

from django.conf import settings
from django.core.mail import get_connection
from django.core.mail.message import make_msgid

from mailer.models import (
    Message, MessageLog, RESULT_SUCCESS, RESULT_FAILURE, get_message_id,
)


# when queue is empty, how long to wait (in seconds) before checking again
EMPTY_QUEUE_SLEEP = getattr(settings, "MAILER_EMPTY_QUEUE_SLEEP", 30)

# lock timeout value. how long to wait for the lock to become available.
# default behavior is to never wait for the lock to be available.
LOCK_WAIT_TIMEOUT = getattr(settings, "MAILER_LOCK_WAIT_TIMEOUT", -1)

# allows for a different lockfile path. The default is a file
# in the current working directory.
LOCK_PATH = getattr(settings, "MAILER_LOCK_PATH", None)


def prioritize():
    """
    Yield the messages in the queue in the order they should be sent.
    """

    while True:
        hp_qs = Message.objects.high_priority().using('default')
        mp_qs = Message.objects.medium_priority().using('default')
        lp_qs = Message.objects.low_priority().using('default')
        while hp_qs.count() or mp_qs.count():
            while hp_qs.count():
                for message in hp_qs.order_by("when_added"):
                    yield message
            while hp_qs.count() == 0 and mp_qs.count():
                yield mp_qs.order_by("when_added")[0]
        while hp_qs.count() == 0 and mp_qs.count() == 0 and lp_qs.count():
            yield lp_qs.order_by("when_added")[0]
        if Message.objects.non_deferred().using('default').count() == 0:
            break


def ensure_message_id(msg):
    if get_message_id(msg) is None:
        msg.extra_headers['Message-ID'] = make_msgid()


def _limits_reached(sent, deferred):
    # Allow sending a fixed/limited amount of emails in each delivery run
    # defaults to None which means send everything in the queue
    EMAIL_MAX_BATCH = getattr(settings, "MAILER_EMAIL_MAX_BATCH", None)

    if EMAIL_MAX_BATCH is not None and sent >= EMAIL_MAX_BATCH:
        logging.info("EMAIL_MAX_BATCH (%s) reached, "
                     "stopping for this round", EMAIL_MAX_BATCH)
        return True

    # Stop sending emails in the current round if more than X emails get
    # deferred - defaults to None which means keep going regardless
    EMAIL_MAX_DEFERRED = getattr(settings, "MAILER_EMAIL_MAX_DEFERRED", None)

    if EMAIL_MAX_DEFERRED is not None and deferred >= EMAIL_MAX_DEFERRED:
        logging.warning("EMAIL_MAX_DEFERRED (%s) reached, "
                        "stopping for this round", EMAIL_MAX_DEFERRED)
        return True


def _throttle_emails():
    # When delivering, wait some time between emails to avoid server overload
    # defaults to 0 for no waiting
    EMAIL_THROTTLE = getattr(settings, "MAILER_EMAIL_THROTTLE", 0)

    if EMAIL_THROTTLE:
        logging.debug("Throttling email delivery. "
                      "Sleeping %s seconds", EMAIL_THROTTLE)
        time.sleep(EMAIL_THROTTLE)


def acquire_lock():
    logging.debug("acquiring lock...")
    if LOCK_PATH is not None:
        lock_file_path = LOCK_PATH
    else:
        lock_file_path = "send_mail"

    lock = lockfile.FileLock(lock_file_path)

    try:
        lock.acquire(LOCK_WAIT_TIMEOUT)
    except lockfile.AlreadyLocked:
        logging.debug("lock already in place. quitting.")
        return False, lock
    except lockfile.LockTimeout:
        logging.debug("waiting for the lock timed out. quitting.")
        return False, lock
    logging.debug("acquired.")
    return True, lock


def release_lock(lock):
    logging.debug("releasing lock...")
    lock.release()
    logging.debug("released.")


def send_all():
    """
    Send all eligible messages in the queue.
    """
    # The actual backend to use for sending, defaulting to the Django default.
    # To make testing easier this is not stored at module level.
    EMAIL_BACKEND = getattr(
        settings,
        "MAILER_EMAIL_BACKEND",
        "django.core.mail.backends.smtp.EmailBackend"
    )

    acquired, lock = acquire_lock()
    if not acquired:
        return

    start_time = time.time()

    deferred = 0
    sent = 0

    try:
        connection = None
        for message in prioritize():
            try:
                if connection is None:
                    connection = get_connection(backend=EMAIL_BACKEND)
                logging.info("sending message '{0}' to {1}".format(
                    message.subject,
                    ", ".join(message.to_addresses))
                )
                email = message.email
                if email is not None:
                    email.connection = connection
                    if not hasattr(email, 'reply_to'):
                        # Compatability fix for EmailMessage objects
                        # pickled when running < Django 1.8 and then
                        # unpickled under Django 1.8
                        email.reply_to = []
                    ensure_message_id(email)
                    email.send()

                    # connection can't be stored in the MessageLog
                    email.connection = None
                    message.email = email  # For the sake of MessageLog
                    MessageLog.objects.log(message, RESULT_SUCCESS)
                    sent += 1
                else:
                    logging.warning("message discarded due to failure in converting from DB. Added on '%s' with priority '%s'" % (message.when_added, message.priority))  # noqa
                message.delete()

            except (socket_error, smtplib.SMTPSenderRefused,
                    smtplib.SMTPRecipientsRefused,
                    smtplib.SMTPDataError,
                    smtplib.SMTPAuthenticationError) as err:
                message.defer()
                logging.info("message deferred due to failure: %s" % err)
                MessageLog.objects.log(message, RESULT_FAILURE, log_message=str(err))
                deferred += 1
                # Get new connection, it case the connection itself has an error.
                connection = None

            # Check if we reached the limits for the current run
            if _limits_reached(sent, deferred):
                break

            _throttle_emails()

    finally:
        release_lock(lock)

    logging.info("")
    logging.info("%s sent; %s deferred;" % (sent, deferred))
    logging.info("done in %.2f seconds" % (time.time() - start_time))


def send_loop():
    """
    Loop indefinitely, checking queue at intervals of EMPTY_QUEUE_SLEEP and
    sending messages if any are on queue.
    """

    while True:
        while not Message.objects.all():
            logging.debug("sleeping for %s seconds before checking queue again" % EMPTY_QUEUE_SLEEP)
            time.sleep(EMPTY_QUEUE_SLEEP)
        send_all()
