import logging

from django.core.management.base import BaseCommand

from mailer.models import RESULT_FAILURE, RESULT_SUCCESS, MessageLog

RESULT_CODES = {"success": [RESULT_SUCCESS], "failure": [RESULT_FAILURE], "all": [RESULT_SUCCESS, RESULT_FAILURE]}

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Delete mailer log"

    def add_arguments(self, parser):
        parser.add_argument("days", type=int)
        parser.add_argument(
            "-r",
            "--result",
            choices=RESULT_CODES.keys(),
            help="Delete logs of messages with the given result code(s) (default: success)",
        )

    def handle(self, *args, **options):
        days = options["days"]
        result_codes = RESULT_CODES.get(options["result"])

        count = MessageLog.objects.purge_old_entries(days, result_codes)
        logger.info(f"{count} log entries deleted ")
