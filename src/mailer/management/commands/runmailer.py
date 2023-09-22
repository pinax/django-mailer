import sys
from datetime import datetime

from django.core.management import BaseCommand

from mailer.engine import send_loop


class Command(BaseCommand):
    """Start the django-mailer send loop"""

    def handle(self, *args, **options):
        self.stdout.write(datetime.now().strftime("%B %d, %Y - %X"))
        self.stdout.write("Starting django-mailer send loop.")
        quit_command = "CTRL-BREAK" if sys.platform == "win32" else "CONTROL-C"
        self.stdout.write(f"Quit the loop with {quit_command}.")
        send_loop()
