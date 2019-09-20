# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations

# This might be a no-op migration on some installations. However, some
# installations will have had EmailField with a default max_length=75 (pre
# Django 1.7), and we didn't account for this properly before, so this migration
# fixes everything to be max_length=254 in case it wasn't.


class Migration(migrations.Migration):

    dependencies = [
        ('mailer', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dontsendentry',
            name='to_address',
            field=models.EmailField(max_length=254),
        ),
    ]
