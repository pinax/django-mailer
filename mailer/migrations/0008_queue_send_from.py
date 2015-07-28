# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('mailer', '0007_auto_20150728_1250'),
    ]

    operations = [
        migrations.AddField(
            model_name='queue',
            name='send_from',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
    ]
