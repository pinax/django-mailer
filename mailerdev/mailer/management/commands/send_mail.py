from django.core.management.base import NoArgsCommand
from mailer.engine import send_all

class Command(NoArgsCommand):
    help = 'Do one pass through the mail queue, attempting to send all mail.'
    
    def handle_noargs(self, **options):
        send_all()
