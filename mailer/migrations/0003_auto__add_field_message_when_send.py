# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Message.when_send'
        db.add_column('mailer_message', 'when_send',
                      self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime(2013, 1, 4, 0, 0)),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Message.when_send'
        db.delete_column('mailer_message', 'when_send')


    models = {
        'mailer.dontsendentry': {
            'Meta': {'object_name': 'DontSendEntry'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'to_address': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            'when_added': ('django.db.models.fields.DateTimeField', [], {})
        },
        'mailer.message': {
            'Meta': {'object_name': 'Message'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message_data': ('django.db.models.fields.TextField', [], {}),
            'priority': ('django.db.models.fields.CharField', [], {'default': "'2'", 'max_length': '1'}),
            'sending_delay': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'when_added': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'when_send': ('django.db.models.fields.DateTimeField', [], {})
        },
        'mailer.messagelog': {
            'Meta': {'object_name': 'MessageLog'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'log_message': ('django.db.models.fields.TextField', [], {}),
            'message_data': ('django.db.models.fields.TextField', [], {}),
            'priority': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
            'result': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
            'when_added': ('django.db.models.fields.DateTimeField', [], {}),
            'when_attempted': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'})
        }
    }

    complete_apps = ['mailer']