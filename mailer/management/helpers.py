from optparse import make_option
from django.core.management.base import BaseCommand

help_msg = "If 1 don't print messagges, but only errors."


if hasattr(BaseCommand, 'option_list') and BaseCommand.option_list:
    # pre django 1.8; use optparse
    class CronArgMixin(object):
        base_options = (
            make_option('-c', '--cron', default=0, type='int', help=help_msg),
        )
        option_list = BaseCommand.option_list + base_options
else:
    # django 1.8+; use argparse
    class CronArgMixin(object):
        def add_arguments(self, parser):
            parser.add_argument(
                '-c',
                '--cron',
                default=0,
                type=int,
                help=help_msg,
            )
