# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mailer', '0009_remove_queue_send_from'),
    ]

    operations = [
        migrations.AlterField(
            model_name='message',
            name='queue',
            field=models.ForeignKey(default=0, to='mailer.Queue'),
        ),
    ]
