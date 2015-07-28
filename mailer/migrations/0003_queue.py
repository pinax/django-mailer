# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mailer', '0002_auto_20150720_1433'),
    ]

    operations = [
        migrations.CreateModel(
            name='Queue',
            fields=[
                ('name', models.TextField(max_length=24, serialize=False, primary_key=True)),
                ('mail_enabled', models.BooleanField(default=True)),
            ],
        ),
    ]
