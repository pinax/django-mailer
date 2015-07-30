from time import mktime
import logging
from datetime import datetime, timedelta
import time
import pytz
import json

import lockfile

from django.conf import settings
from django.core.mail import get_connection
from django.utils import timezone

from mailer.models import Message, MessageLog, RESULT_SUCCESS, RESULT_FAILURE, Queue


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
    lock = lockfile.FileLock("send_mail")

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


def defer_messages(qs):
    for msg in qs:
        msg.defer()


class SpamThresholdHit(Exception):
    pass


class MultipleValidationErrors(Exception):
    pass


def send_all_with_checks():
    errors = []
    for queue in Queue.objects.all():
        try:
            do_checks(queue)
        except SpamThresholdHit as e:
            errors.append(e)

    send_all()

    if errors:
        raise MultipleValidationErrors(errors)


def do_checks(queue):
    metadata = json.loads(queue.metadata)

    if settings.USE_TZ:
        when_added = timezone.localtime(timezone.now()) - timedelta(hours=metadata['limits']['age'])
    else:
        when_added = datetime.now() - timedelta(hours=metadata['limits']['age'])
    qs = (Message.objects.filter(queue=queue, priority__lt=4,
                                 when_added__lt=when_added).order_by('id'))
    if len(qs) > 0:
        defer_messages(qs)

    # Check messages in last hour against spam threshold for weekdays and
    # weekends
    qs = Message.objects.filter(priority__lt=4, queue=queue).order_by('id')
    qs_len = len(qs)
    if datetime.now().weekday() < 5:
        if qs_len > metadata['limits']['weekday']:
            defer_messages(qs)
            msg = ('spam prevention threshold (%s) exceeded on queue:'
                   ' \'%s\' with %s %s. IDs: %s -> %s')
            raise SpamThresholdHit(msg % (metadata['limits']['weekday'], queue,
                                          qs_len,
                                          'message' if qs_len == 1 else 'messages',
                                          qs[0].id, qs[qs_len - 1].id))
    else:
        if qs_len > metadata['limits']['weekend']:
            defer_messages(qs)
            msg = ('spam prevention threshold (%s) exceeded on queue:'
                   ' \'%s\' with %s %s. IDs: %s -> %s')
            raise SpamThresholdHit(msg % (metadata['limits']['weekend'], queue,
                                          qs_len,
                                          'message' if qs_len == 1 else 'messages',
                                          qs[0].id, qs[qs_len - 1].id))


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
                if message.queue.mail_enabled is False:
                    logging.info("message skipped as queue for '{0}'"
                                 " is disabled".format(message.queue.name))
                    deferred += 1
                    message.defer()
                    continue
                if connection is None:
                    connection = get_connection(backend=EMAIL_BACKEND)
                logging.info("sending message '{0}' to {1}".format(
                    message.subject.encode("utf-8"),
                    u", ".join(message.to_addresses).encode("utf-8"))
                )
                email = message.email
                if email is not None:
                    email.connection = connection
                    email.send()
                    MessageLog.objects.log(message, RESULT_SUCCESS,
                                           queue=message.queue)
                    sent += 1
                else:
                    msg = ("message discarded due to failure in converting from"
                           "DB. Added on '%s' with priority '%s'")
                    logging.warning(msg % (message.when_added,
                                    message.priority))  # noqa
                message.delete()

            except Exception as err:
                message.defer()
                logging.info("message deferred due to failure (%s): %s"
                             % (err.__class__.__name__, err))
                MessageLog.objects.log(message, RESULT_FAILURE,
                                       log_message=str(err), queue=message.queue)
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
            logging.debug("sleeping for %s seconds before checking queue again"
                          % EMPTY_QUEUE_SLEEP)
            time.sleep(EMPTY_QUEUE_SLEEP)
        send_all()


def resend(queues, send_from=None):
    for queueName in queues:
        try:
            queue = Queue.objects.get(name=queueName)
            if queue.mail_enabled == 0:
                queue.mail_enabled = 1
                queue.save()
                logging.info(('Mail queue: {0} enabled').format(queue.name))

            if send_from:
                conv_send_from = time.strptime(send_from, "%Y-%m-%d %H:%M")
                conv_send_from = datetime.fromtimestamp(mktime(conv_send_from))
                tz = pytz.utc
                conv_send_from = (tz.localize(conv_send_from, is_dst=None)
                                  .astimezone(pytz.utc).replace(tzinfo=None))
                messages = Message.objects.filter(queue=queue,
                                                  when_added__gte=conv_send_from)

                for message in messages:
                    message.priority = 2
                    message.save()

                logging.info(('Resending mail on queue {0} from {1}')
                             .format(queue, conv_send_from))
            else:
                messages = Message.objects.filter(queue=queue)
                for message in messages:
                    message.priority = 2
                    message.save()

        except Queue.DoesNotExist:
            logging.warning(('Queue {0} not found').format(queueName))
