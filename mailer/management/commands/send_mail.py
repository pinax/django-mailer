import logging
from optparse import make_option

from django.conf import settings
from django.core.management.base import NoArgsCommand
from django.db import connection

from mailer.engine import send_all


# allow a sysadmin to pause the sending of mail temporarily.
PAUSE_SEND = getattr(settings, "MAILER_PAUSE_SEND", False)


class Command(NoArgsCommand):
    help = "Do one pass through the mail queue, attempting to send all mail."
    base_options = (
        make_option('-c', '--cron', default=0, type='int',
            help='If 1 don\'t print messagges, but only errors.'
        ),
    )
    option_list = NoArgsCommand.option_list + base_options
    
    def handle_noargs(self, **options):
        if options['cron'] == 0:
            logging.basicConfig(level=logging.DEBUG, format="%(message)s")
        else:
            logging.basicConfig(level=logging.ERROR, format="%(message)s")
        logging.info("-" * 72)
        # if PAUSE_SEND is turned on don't do anything.
        if not PAUSE_SEND:
            send_all()
        else:
            logging.info("sending is paused, quitting.")
        connection.close()
