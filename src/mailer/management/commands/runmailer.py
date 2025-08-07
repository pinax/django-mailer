import logging
import sys
from argparse import ArgumentParser
from contextlib import suppress
from datetime import datetime

from django.core.management import BaseCommand

from mailer.engine import send_loop


class Command(BaseCommand):
    """Start the django-mailer send loop"""

    def add_arguments(self, parser: ArgumentParser):
        parser.add_argument("--debug", action="store_true", help="Increase logging level for django_mailer to DEBUG")
        return super().add_arguments(parser)

    def handle(self, *args, **options):
        if options["debug"]:
            for name in ["mailer.engine"]:
                logger = logging.getLogger(name)
                logger.setLevel(logging.DEBUG)
                for handler in logger.handlers:
                    handler.level = logging.DEBUG

        self.stdout.write(datetime.now().strftime("%B %d, %Y - %X"))
        self.stdout.write("Starting django-mailer send loop.")
        quit_command = "CTRL-BREAK" if sys.platform == "win32" else "CONTROL-C"
        self.stdout.write(f"Quit the loop with {quit_command}.")
        with suppress(KeyboardInterrupt):
            send_loop()
