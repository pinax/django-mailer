import time
import logging
from optparse import make_option
from django.core.management.base import BaseCommand

from django.conf import settings

from mailer.models import Queue, Message

from mailer.engine import resend

class Command(BaseCommand):
    help = "Attempt to send mail in a specific queue. Optional send from time."

    def add_arguments(self, parser):
        parser.add_argument('queue', nargs='+', type=str)
        parser.add_argument('--send_from', dest='send_from', default=time.strftime("%Y-%m-%d %H:%M"))

    def handle(self, *args, **options):
        resend(options['queue'], options['send_from'])
