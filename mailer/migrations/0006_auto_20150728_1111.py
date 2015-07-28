# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mailer', '0005_auto_20150728_1052'),
    ]

    operations = [
        migrations.AlterField(
            model_name='queue',
            name='name',
            field=models.CharField(max_length=24),
        ),
    ]
