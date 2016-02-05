import logging
from django.core.management.base import BaseCommand
from mailer.models import MessageLog


class Command(BaseCommand):
    help = "Delete mailer log"

    def add_arguments(self, parser):
        parser.add_argument('days', nargs=1, type=int)

    def handle(self, *args, **options):
        count = MessageLog.objects.purge_old_entries(options['days'][0])
        logging.info("%s log entries deleted " % count)
