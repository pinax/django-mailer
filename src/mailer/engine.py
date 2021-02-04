from __future__ import unicode_literals

import contextlib
import datetime
import logging
import smtplib
import time
from socket import error as socket_error
from itertools import cycle

import lockfile
from django import VERSION as DJANGO_VERSION
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail import get_connection
from django.core.mail.message import make_msgid
from django.db import DatabaseError, NotSupportedError, OperationalError, transaction
from mailer.models import (RESULT_FAILURE, RESULT_SUCCESS, Message, MessageLog, get_message_id)
from mailer.utils import EmailThread


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

# Get daily sending limit per account
DAILY_SENDING_LIMIT_PER_ACCOUNT = getattr(settings, 'MAILER_DAILY_SENDING_LIMIT_PER_ACCOUNT', 0)

# Get sending limit per run
SENDING_LIMIT_PER_RUN = getattr(settings, 'MAILER_SENDING_LIMIT_PER_RUN', 0)

# Get list of accounts
ACCOUNTS_LIST = getattr(settings, 'MAILER_EMAIL_ACCOUNT_LIST', None)

# Use async_send to deliver mail
ASYNC_SEND = getattr(settings, 'MAILER_ASYNC_SEND', False)


def prioritize(limit):
    """
    Returns the messages in the queue in the order they should be sent.
    """
    return Message.objects.non_deferred().order_by('priority', 'when_added')[:limit]


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


def get_messages_for_sending(limit):
    """
    Returns a series of context managers that are used for sending mails in the queue.
    Entering the context manager returns the actual message
    """
    for message in prioritize(limit):
        yield sender_context(message)


def ensure_message_id(msg):
    if get_message_id(msg) is None:
        msg.extra_headers['Message-ID'] = make_msgid()


def send_async_mail(email, message, account):
    t = EmailThread(email)
    t.start()

    # Exception handled in Caller thread 
    try: 
        t.join() 

        # connection can't be stored in the MessageLog
        email.connection = None
        message.email = email  # For the sake of MessageLog
        MessageLog.objects.log(message, RESULT_SUCCESS, account=account)
        
        message.delete()
    except Exception as e: 
        message.defer()
        logging.info("Message deferred due to failure: %s" % e)
        MessageLog.objects.log(message, RESULT_FAILURE, log_message=str(e), account=account)


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


def _require_no_backend_loop(mailer_email_backend):
    if mailer_email_backend == settings.EMAIL_BACKEND == 'mailer.backend.DbBackend':
        raise ImproperlyConfigured('EMAIL_BACKEND and MAILER_EMAIL_BACKEND'
                                   ' should not both be set to "{}"'
                                   ' at the same time'
                                   .format(settings.EMAIL_BACKEND))


def _require_account_list():
    if not ACCOUNTS_LIST or len(ACCOUNTS_LIST) < 1:
        raise ImproperlyConfigured('MAILER_EMAIL_ACCOUNT_LIST should be set.')


def get_account_limit(account):
    to_send_per_account = 0

    sent_today_count = MessageLog.objects.filter(
        account=account,
        result=RESULT_SUCCESS,
        when_attempted__gt=datetime.datetime.now() - datetime.timedelta(days=1)
    ).count()

    if DAILY_SENDING_LIMIT_PER_ACCOUNT:
        to_send_per_account = DAILY_SENDING_LIMIT_PER_ACCOUNT - sent_today_count

    if to_send_per_account <= 0:
        logging.warn("Daily sending limit of {limit} reached for account {account}".format(
            limit=DAILY_SENDING_LIMIT_PER_ACCOUNT,
            account=account)
        )

    if SENDING_LIMIT_PER_RUN and to_send_per_account > SENDING_LIMIT_PER_RUN:
        to_send_per_account = SENDING_LIMIT_PER_RUN

    return to_send_per_account


def get_next_mail_account():
    # get last account used
    count = 0
    account_list = cycle(ACCOUNTS_LIST)
    account_list_size = len(ACCOUNTS_LIST)
    account_limit_reached = 0
    # get first in the list
    nextelem = next(account_list)
    # get last messagelog
    last_message = MessageLog.objects.last()
    if not last_message:
        # return first
        account = nextelem['EMAIL_HOST_USER']
        return nextelem, get_account_limit(account)
    account_user = last_message.account
    while True:
        count += 1
        if account_limit_reached >= account_list_size:
            return None, 0

        thiselem, nextelem = nextelem, next(account_list)
        if thiselem['EMAIL_HOST_USER'] == account_user:
            try:
                account = nextelem['EMAIL_HOST_USER']

                to_send_per_account = get_account_limit(account)
                if to_send_per_account <= 0:
                    account_limit_reached += 1
                    account_user = account
                    continue

                # return nextelem if account is equal to last account used and not reached daily limit
                return nextelem, to_send_per_account
            except KeyError:
                logging.warn('Skipping account due to failure to pull settings')
                continue
        else:
            if count > account_list_size:
                # return first
                account = thiselem['EMAIL_HOST_USER']
                return thiselem, get_account_limit(account)


def send_all():
    """
    Send all eligible messages in the queue.
    """
    # The actual backend to use for sending, defaulting to the Django default.
    # To make testing easier this is not stored at module level.
    mailer_email_backend = getattr(
        settings,
        "MAILER_EMAIL_BACKEND",
        "django.core.mail.backends.smtp.EmailBackend"
    )

    _require_no_backend_loop(mailer_email_backend)

    _require_account_list()

    acquired, lock = acquire_lock()
    if not acquired:
        return

    start_time = time.time()
    sent = 0
    deferred = 0
    to_send_per_account = 0

    try:
        mail_account, to_send_per_account = get_next_mail_account()
        connection = None
        if mail_account:
            for context in get_messages_for_sending(to_send_per_account):
                with context as message:
                    if message is None:
                        # We didn't acquire the lock
                        continue

                    account = mail_account['EMAIL_HOST_USER']
                    try:
                        if connection is None:
                            connection = get_connection(
                                backend=mailer_email_backend,
                                host=mail_account['EMAIL_HOST'],
                                port=mail_account['EMAIL_PORT'],
                                username=mail_account['EMAIL_HOST_USER'],
                                password=mail_account['EMAIL_HOST_PASSWORD'],
                                use_tls=mail_account['EMAIL_USE_TLS'],
                            )

                        logging.info("Sending message '{0}' to {1} using account {2}".format(
                            message.subject,
                            ", ".join(message.to_addresses),
                            account
                        ))

                        email = message.email
                        if email is None:
                            logging.warning(
                                "Message discarded due to failure in converting from DB. Added on '%s' with priority '%s'" % (
                                message.when_added, message.priority))  # noqa
                        else:
                            email.connection = connection
                            ensure_message_id(email)
                            if ASYNC_SEND:
                                send_async_mail(email, message, account)
                                sent += 1
                            else:
                                email.send()

                                # connection can't be stored in the MessageLog
                                email.connection = None
                                message.email = email  # For the sake of MessageLog
                                MessageLog.objects.log(message, RESULT_SUCCESS, account=account)
                                sent += 1
                                
                                message.delete()

                    except (socket_error, smtplib.SMTPSenderRefused,
                            smtplib.SMTPRecipientsRefused,
                            smtplib.SMTPDataError,
                            smtplib.SMTPAuthenticationError) as err:
                        message.defer()
                        logging.info("Message deferred due to failure: %s" % err)
                        MessageLog.objects.log(message, RESULT_FAILURE, log_message=str(err), account=account)
                        deferred += 1
                        # Get new connection, it case the connection itself has an error.
                        connection = None

                # Check if we reached the limits for the current run
                if _limits_reached(sent, deferred):
                    break

                _throttle_emails()
        else:
            logging.info('No account available to send messages.') 

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
