import logging

from django.core.management.base import BaseCommand

from mailer.models import Message
from mailer.management.helpers import setup_logger, CronArgMixin

logger = logging.getLogger(__name__)


class Command(CronArgMixin, BaseCommand):
    help = "Attempt to resend any deferred mail."

    def handle(self, *args, **options):
        if options['cron'] == 0:
            setup_logger(logger, level=logging.DEBUG)
        else:
            setup_logger(logger, level=logging.ERROR)
        count = Message.objects.retry_deferred()  # @@@ new_priority not yet supported
        logger.info("%s message(s) retried" % count)
