# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mailer', '0008_queue_send_from'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='queue',
            name='send_from',
        ),
    ]
