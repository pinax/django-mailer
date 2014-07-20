import time
import smtplib
import logging

from mailer.lockfile import FileLock, AlreadyLocked, LockTimeout
from socket import error as socket_error

from django.conf import settings
try:
    # Django 1.2
    from django.core.mail import get_connection
except ImportError:
    # ImportError: cannot import name get_connection
    from django.core.mail import SMTPConnection
    get_connection = lambda backend=None, fail_silently=False, **kwds: SMTPConnection(fail_silently=fail_silently)  # noqa

from mailer.models import Message, MessageLog


# when queue is empty, how long to wait (in seconds) before checking again
EMPTY_QUEUE_SLEEP = getattr(settings, "MAILER_EMPTY_QUEUE_SLEEP", 30)

# lock timeout value. how long to wait for the lock to become available.
# default behavior is to never wait for the lock to be available.
LOCK_WAIT_TIMEOUT = getattr(settings, "MAILER_LOCK_WAIT_TIMEOUT", -1)


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

    lock = FileLock("send_mail")

    logging.debug("acquiring lock...")
    try:
        lock.acquire(LOCK_WAIT_TIMEOUT)
    except AlreadyLocked:
        logging.debug("lock already in place. quitting.")
        return
    except LockTimeout:
        logging.debug("waiting for the lock timed out. quitting.")
        return
    logging.debug("acquired.")

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
                    message.subject.encode("utf-8"),
                    u", ".join(message.to_addresses).encode("utf-8"))
                )
                email = message.email
                email.connection = connection
                email.send()
                MessageLog.objects.log(message, 1)  # @@@ avoid using literal result code
                message.delete()
                sent += 1
            except (socket_error, smtplib.SMTPSenderRefused, smtplib.SMTPRecipientsRefused, smtplib.SMTPAuthenticationError) as err:  # noqa
                message.defer()
                logging.info("message deferred due to failure: %s" % err)
                MessageLog.objects.log(message, 3, log_message=str(err))  # @@@ avoid using literal result code # noqa
                deferred += 1
                # Get new connection, it case the connection itself has an error.
                connection = None
    finally:
        logging.debug("releasing lock...")
        lock.release()
        logging.debug("released.")

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
