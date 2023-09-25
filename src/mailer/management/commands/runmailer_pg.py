import logging
import sys
from argparse import ArgumentParser
from datetime import datetime

from django.core.management import BaseCommand


class Command(BaseCommand):
    """Start the django-mailer send loop"""

    def add_arguments(self, parser: ArgumentParser):
        parser.add_argument("--debug", action="store_true", help="Increase logging level for django_mailer to DEBUG")
        return super().add_arguments(parser)

    def handle(self, *args, **options):
        from mailer.postgres import postgres_send_loop

        if options["debug"]:
            for name in ["mailer.engine", "mailer.postgres"]:
                logger = logging.getLogger(name)
                logger.setLevel(logging.DEBUG)
                for handler in logger.handlers:
                    handler.level = logging.DEBUG

        # For sake of those who haven't configured logger, we print something to stdout
        self.stdout.write(datetime.now().strftime("%B %d, %Y - %X"))
        self.stdout.write("Starting django-mailer send loop.")
        quit_command = "CTRL-BREAK" if sys.platform == "win32" else "CONTROL-C"
        self.stdout.write(f"Quit the loop with {quit_command}.")
        postgres_send_loop()
