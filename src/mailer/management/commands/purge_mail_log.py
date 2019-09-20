import logging
from django.core.management.base import BaseCommand
from mailer.models import MessageLog


class Command(BaseCommand):
    help = "Delete mailer log"

    def add_arguments(self, parser):
        parser.add_argument('days', nargs=1, type=int)

    def handle(self, *args, **options):
        # Compatiblity with Django-1.6
        days = int(options.get('days', args)[0])
        count = MessageLog.objects.purge_old_entries(days)
        logging.info("%s log entries deleted " % count)
