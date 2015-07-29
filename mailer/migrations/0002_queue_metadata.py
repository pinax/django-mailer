# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mailer', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='queue',
            name='metadata',
            field=models.TextField(default='{weekday: 500, weekend: 700}'),
        ),
    ]
