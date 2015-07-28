# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mailer', '0006_auto_20150728_1111'),
    ]

    operations = [
        migrations.AddField(
            model_name='messagelog',
            name='queue',
            field=models.ForeignKey(default=0, to='mailer.Queue'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='queue',
            name='name',
            field=models.CharField(max_length=24, null=True),
        ),
    ]
