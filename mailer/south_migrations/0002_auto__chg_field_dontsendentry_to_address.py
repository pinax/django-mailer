# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


# This looks like a no-op migration (forwards the same as backwards),
# and on some installations it will be. However, some installations
# will have had EmailField with a default max_length=75 (pre Django 1.7),
# and we didn't account for this properly before, so this migration
# fixes everything to be max_length=254 in case it wasn't.

class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'DontSendEntry.to_address'
        db.alter_column('mailer_dontsendentry', 'to_address', self.gf('django.db.models.fields.EmailField')(max_length=254))

    def backwards(self, orm):

        # Changing field 'DontSendEntry.to_address'
        db.alter_column('mailer_dontsendentry', 'to_address', self.gf('django.db.models.fields.EmailField')(max_length=254))

    models = {
        'mailer.dontsendentry': {
            'Meta': {'object_name': 'DontSendEntry'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'to_address': ('django.db.models.fields.EmailField', [], {'max_length': '123'}),
            'when_added': ('django.db.models.fields.DateTimeField', [], {})
        },
        'mailer.message': {
            'Meta': {'object_name': 'Message'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message_data': ('django.db.models.fields.TextField', [], {}),
            'priority': ('django.db.models.fields.CharField', [], {'default': "u'2'", 'max_length': '1'}),
            'when_added': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'})
        },
        'mailer.messagelog': {
            'Meta': {'object_name': 'MessageLog'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'log_message': ('django.db.models.fields.TextField', [], {}),
            'message_data': ('django.db.models.fields.TextField', [], {}),
            'priority': ('django.db.models.fields.CharField', [], {'max_length': '1', 'db_index': 'True'}),
            'result': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
            'when_added': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'when_attempted': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'})
        }
    }

    complete_apps = ['mailer']
