import logging

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection

from mailer.engine import send_all
from mailer.management.helpers import CronArgMixin


# allow a sysadmin to pause the sending of mail temporarily.
PAUSE_SEND = getattr(settings, "MAILER_PAUSE_SEND", False)


class Command(CronArgMixin, BaseCommand):
    help = "Do one pass through the mail queue, attempting to send all mail."

    def handle(self, *args, **options):
        if options['cron'] == 0:
            logging.basicConfig(level=logging.DEBUG, format="%(message)s")
        else:
            logging.basicConfig(level=logging.ERROR, format="%(message)s")
        logging.info("-" * 72)
        # if PAUSE_SEND is turned on don't do anything.
        if not PAUSE_SEND:
            send_all()
        else:
            logging.info("sending is paused, quitting.")
        connection.close()
