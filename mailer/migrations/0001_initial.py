# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='DontSendEntry',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('to_address', models.EmailField(max_length=254)),
                ('when_added', models.DateTimeField()),
            ],
            options={
                'verbose_name': "don't send entry",
                'verbose_name_plural': "don't send entries",
            },
        ),
        migrations.CreateModel(
            name='Message',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('message_data', models.TextField()),
                ('when_added', models.DateTimeField(default=django.utils.timezone.now)),
                ('priority', models.CharField(default='2', max_length=1, choices=[('1', 'high'), ('2', 'medium'), ('3', 'low'), ('4', 'deferred')])),
            ],
            options={
                'verbose_name': 'message',
                'verbose_name_plural': 'messages',
            },
        ),
        migrations.CreateModel(
            name='MessageLog',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('message_data', models.TextField()),
                ('when_added', models.DateTimeField(db_index=True)),
                ('priority', models.CharField(db_index=True, max_length=1, choices=[('1', 'high'), ('2', 'medium'), ('3', 'low'), ('4', 'deferred')])),
                ('when_attempted', models.DateTimeField(default=django.utils.timezone.now)),
                ('result', models.CharField(max_length=1, choices=[('1', 'success'), ('2', "don't send"), ('3', 'failure')])),
                ('log_message', models.TextField()),
            ],
            options={
                'verbose_name': 'message log',
                'verbose_name_plural': 'message logs',
            },
        ),
    ]
