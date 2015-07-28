# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mailer', '0004_auto_20150728_1045'),
    ]

    operations = [
        migrations.AddField(
            model_name='message',
            name='queue',
            field=models.ForeignKey(default='', to='mailer.Queue'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='queue',
            name='id',
            field=models.AutoField(auto_created=True, primary_key=True, default=1, serialize=False, verbose_name='ID'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='queue',
            name='name',
            field=models.CharField(unique=True, max_length=24),
        ),
    ]
