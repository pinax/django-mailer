import logging
from optparse import make_option

from django.core.management.base import NoArgsCommand
from django.db import connection

from mailer.models import Message


class Command(NoArgsCommand):
    help = "Attempt to resend any deferred mail."
    base_options = (
        make_option('-c', '--cron', default=0, type='int', help='If 1 don\'t print messagges, but only errors.'),  # noqa
    )
    option_list = NoArgsCommand.option_list + base_options

    def handle_noargs(self, **options):
        if options['cron'] == 0:
            logging.basicConfig(level=logging.DEBUG, format="%(message)s")
        else:
            logging.basicConfig(level=logging.ERROR, format="%(message)s")
        count = Message.objects.retry_deferred()  # @@@ new_priority not yet supported
        logging.info("%s message(s) retried" % count)
        connection.close()
