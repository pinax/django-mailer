import logging

from django.core.management.base import BaseCommand
from django.db import connection

from mailer.models import Message
from mailer.management.helpers import CronArgMixin


class Command(CronArgMixin, BaseCommand):
    help = "Attempt to resend any deferred mail."

    def handle(self, *args, **options):
        if options['cron'] == 0:
            logging.basicConfig(level=logging.DEBUG, format="%(message)s")
        else:
            logging.basicConfig(level=logging.ERROR, format="%(message)s")
        count = Message.objects.retry_deferred()  # @@@ new_priority not yet supported
        logging.info("%s message(s) retried" % count)
        connection.close()
