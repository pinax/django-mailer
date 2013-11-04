import logging

from datetime import timedelta
from django.conf import settings
from django.utils import timezone
from django.core.management.base import NoArgsCommand

from mailer.models import MessageLog


class Command(NoArgsCommand):
    help = "Deletes all log messages from the database"

    def handle_noargs(self, **options):
        period = timezone.now() - timedelta(
            days=getattr(settings, 'MAILER_LOG_DAYS', 7))

        messages = MessageLog.objects.filter(when_added__lt=period)
        count = messages.count()  # get a number of log messages
        # messages.delete()  # delete log messages
        logging.info("%s log message(s) deleted" % count)
