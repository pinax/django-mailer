import logging
import queue
import select
import signal
import sys
import threading
import time
from dataclasses import dataclass
from datetime import datetime

from django.db import connections

from mailer.engine import EMPTY_QUEUE_SLEEP, send_all
from mailer.models import Message

is_psycopg3_available = False
try:
    import psycopg  # noqa: F401
except ImportError:
    try:
        import psycopg2.extensions
    except ImportError:
        raise ImportError("Either psycopg or psycopg2 must be installed.")
else:
    is_psycopg3_available = True

logger = logging.getLogger(__name__)


notify_q = queue.Queue()


CHANNEL = "django_mailer_new_message"


def postgres_send_loop():
    """
    Loop indefinitely, checking queue using NOTIFY/LISTEN and running send_all(),
    and additional running every MAILER_EMPTY_QUEUE_SLEEP seconds.
    """
    # See
    # psycopg2
    # https://www.psycopg.org/docs/advanced.html#asynchronous-notifications
    #
    # psycopg3
    # https://www.psycopg.org/psycopg3/docs/advanced/async.html#asynchronous-notifications

    # Get a connection, for a few lower level operations.
    dj_conn = connections[Message.objects.db]
    if dj_conn.connection is None:
        dj_conn.connect()
    conn = dj_conn.connection

    # We want autocommit for timely notifications
    use_autocommit(conn)

    curs = conn.cursor()
    install_trigger(curs, dj_conn)
    curs.execute(f"LISTEN {CHANNEL};")
    logger.debug(f"Waiting for notifications on channel '{CHANNEL}'")

    # We have a single worker thread that runs send_all(). This means we are not
    # sending messages in parallel, which is deliberate - in many cases email
    # sending may be throttled and we are less likely to exceed quotas if we
    # send in serial rather than parallel.
    worker_thread = threading.Thread(target=worker, daemon=True)
    worker_thread.start()

    if EMPTY_QUEUE_SLEEP is not None:
        beat_thread = threading.Thread(target=beat, daemon=True)
        beat_thread.start()
    else:
        beat_thread = None

    def signal_handler(signal, frame):
        logger.debug("Received SIGINT, shutting down")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    if is_psycopg3_available:
        gen = conn.notifies()
        for notify in gen:
            add_item_to_queue(notify)
    else:
        SELECT_TIMEOUT = 5
        while True:
            if select.select([conn], [], [], SELECT_TIMEOUT) == ([], [], []):
                # timeout
                pass
            else:
                conn.poll()
                try:
                    last = conn.notifies.pop()
                except IndexError:
                    # Not entirely sure how this happens, but it could only happen
                    # if `notifies` is empty, because there are no more notifications
                    # to process.
                    continue

                # We don't care about payload or how many NOTIFY there were,
                # we'll just run once, so drop the rest:
                to_drop = conn.notifies
                if to_drop:
                    # This happens if several messages were inserted in the same
                    # transaction - we get multiple items on `conn.notifies` after a
                    # single `conn.poll()`
                    logger.debug("Dropping notifications %r", to_drop)
                conn.notifies.clear()

                # Add to queue
                add_item_to_queue(last)

    # Clean up:
    worker_thread.join()
    if beat_thread is not None:
        beat_thread.join()


def use_autocommit(conn):
    if is_psycopg3_available:
        conn.autocommit = True
    else:
        conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)


def install_trigger(curs, dj_conn):
    message_table_name = Message._meta.db_table
    curs.execute(
        f"""
    CREATE OR REPLACE FUNCTION django_mailer_notify_new_message()
    RETURNS TRIGGER AS $$
    BEGIN
      PERFORM pg_notify('{CHANNEL}', NEW.id::text);
      RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;

        """
    )

    # "CREATE OR REPLACE TRIGGER" doesn't exist until Postgresql 14
    curs.execute(
        f"""
    DO $$
    BEGIN
      IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'django_mailer_message_notify_trigger') THEN
        CREATE TRIGGER django_mailer_message_notify_trigger
        AFTER INSERT ON {dj_conn.ops.quote_name(message_table_name)}
        FOR EACH ROW EXECUTE FUNCTION django_mailer_notify_new_message();
      END IF;
    END $$;
    """
    )


def add_item_to_queue(item):
    if notify_q.empty():
        logger.debug("Putting %r on queue", item)
        notify_q.put(item)
    else:
        # notify_q is not empty.

        # Our worker thread always processes all Messages. If it still
        # has an item on the queue, it will process all remaining
        # messages next time it runs, so there is no point adding
        # another item to the non-empty queue - this will just cause
        # `send_all()` to run pointlessly.

        # This could be important for efficiency: if 100 records are
        # inserted into the Message table at the same time, this process
        # will get NOTIFY sent 100 times (unless they were all part of
        # the same transaction). The first `send_all()` command will
        # deal with them all (or a large fraction of them, depending on
        # timing). We don't want `send_all()` to thrash away doing
        # nothing another 99 times afterwards.
        logger.debug("Discarding item %r as work queue is not empty", item)


def worker():
    while True:
        item = notify_q.get()
        logger.debug("Working on %r", item)
        send_all()
        logger.debug("Finished %r", item)
        notify_q.task_done()


@dataclass
class Scheduled:
    now: datetime  # this is used for debugging only, we just need some object on the queue


def beat():
    while True:
        if notify_q.empty():
            scheduled = Scheduled(now=datetime.now())
            logger.debug("Putting scheduled item %r on queue", scheduled)
            notify_q.put(scheduled)
        time.sleep(EMPTY_QUEUE_SLEEP)
