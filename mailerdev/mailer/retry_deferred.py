from django.core.management.base import NoArgsCommand
from mailer.models import Message

class Command(NoArgsCommand):
    help = 'Attempt to resend any deferred mail.'
    
    def handle_noargs(self, **options):
        count = Message.objects.retry_deferred() # @@@ new_priority not yet supported
        print "%s message(s) retried" % count