import logging
import warnings

from django.conf import settings
from django.core.management.base import BaseCommand

from mailer.engine import send_all
from mailer.management.helpers import CronArgMixin

# allow a sysadmin to pause the sending of mail temporarily.
PAUSE_SEND = getattr(settings, "MAILER_PAUSE_SEND", False)

logger = logging.getLogger(__name__)


class Command(CronArgMixin, BaseCommand):
    help = "Do one pass through the mail queue, attempting to send all mail."

    def handle(self, *args, **options):
        if options["cron"]:
            warnings.warn(
                "send_mail's -c/--cron option is no longer necessary and will be removed in a future release",
                DeprecationWarning,
            )
        logger.info("-" * 72)
        # if PAUSE_SEND is turned on don't do anything.
        if not PAUSE_SEND:
            send_all()
        else:
            logger.info("sending is paused, quitting.")
