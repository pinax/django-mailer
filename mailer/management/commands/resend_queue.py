from django.core.management.base import BaseCommand
from mailer.engine import resend


class Command(BaseCommand):
    help = "Attempt to send mail in a specific queue. Optional send from time."

    def add_arguments(self, parser):
        parser.add_argument('queue', nargs='+', type=str)
        parser.add_argument('--send_from', dest='send_from', default=None)

    def handle(self, *args, **options):
        if 'send_from' in options:
            resend(options['queue'], options['send_from'])
        else:
            resend(options['queue'])
