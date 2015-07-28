import time
import logging
from optparse import make_option
from django.core.management.base import BaseCommand

from django.conf import settings

from mailer.models import Queue, Message

from time import mktime
from datetime import datetime

class Command(BaseCommand):
    help = "Attempt to send mail in a specific queue. Optional send from time."

    def add_arguments(self, parser):
        parser.add_argument('queue', nargs='+', type=str)
        parser.add_argument('--send_from', dest='send_from', default=time.strftime("%Y-%m-%d %H:%M"))

    def handle(self, *args, **options):

        for queueName in options['queue']:
            try:
                queue = Queue.objects.get(name=queueName)
                if queue.mail_enabled == 0:
                    queue.mail_enabled = 1
                    queue.save()
                    logging.error(('Mail queue: {0} enabled').format(queue.name))
                    return
                send_from = time.strptime(options['send_from'], "%Y-%m-%d %H:%M")
                send_from = datetime.fromtimestamp(mktime(send_from))
                messages = Message.objects.filter(queue=queue, when_added__gte=send_from)
                for message in messages:
                    message.priority = 2
                    message.save()
            except Queue.DoesNotExist:
                logging.error(('Queue {0} not found').format(queueName))
