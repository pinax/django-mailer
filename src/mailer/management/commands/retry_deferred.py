import logging
import warnings

from django.core.management.base import BaseCommand

from mailer.models import Message
from mailer.management.helpers import CronArgMixin

logger = logging.getLogger(__name__)


class Command(CronArgMixin, BaseCommand):
    help = "Attempt to resend any deferred mail."

    def handle(self, *args, **options):
        if options['cron']:
            warnings.warn("retry_deferred's -c/--cron option is no longer "
                          "necessary and will be removed in a future release",
                          DeprecationWarning)
        count = Message.objects.retry_deferred()  # @@@ new_priority not yet supported
        logger.info("%s message(s) retried" % count)
