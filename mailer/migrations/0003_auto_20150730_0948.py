# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mailer', '0002_queue_metadata'),
    ]

    operations = [
        migrations.AddField(
            model_name='message',
            name='metadata',
            field=models.TextField(default='{}'),
        ),
        migrations.AlterField(
            model_name='queue',
            name='metadata',
            field=models.TextField(default='{"limits":{"weekday": 500, "weekend": 700, "age": 1}}'),
        ),
    ]
