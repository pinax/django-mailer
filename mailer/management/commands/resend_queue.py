import logging
from optparse import make_option

from django.conf import settings
from django.core.management.base import NoArgsCommand
from django.db import connection

from mailer.models import Queue, Message

class Command(NoArgsCommand):
    help = "Attempt to send mail in a specific queue. Optional send from time."

    def add_arguments(self, parser):
        parser.add_argument('queue', nargs='+', type=str)

    def handle(self, *args, **options):
        for queueName in options['queue']:
            try:
                queue = Queue.objects.get(name=queueName)
                if queue.mail_enabled == 0:
                    logging.error(('Mail is not enabled for queue {0}. Please enabled and try again').format(queue.name))
                    return
                messages = Message.objects.filter(queue=queue)
                for message in messages:
                    message.priority = 2
                    message.save()
            except Queue.DoesNotExist:
                logging.error(('Queue {0} not found').format(queueName))
