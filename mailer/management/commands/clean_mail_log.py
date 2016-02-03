from django.core.management.base import BaseCommand
from mailer.models import MessageLog


class Command(BaseCommand):
    help = "Delete mailer log"

    def add_arguments(self, parser):
        parser.add_argument('days', nargs=1, type=int)

    def handle(self, **options):
        MessageLog.objects.cleanup(options['days'][0])
