# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Message'
        db.create_table('mailer_message', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('message_data', self.gf('django.db.models.fields.TextField')()),
            ('when_added', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('priority', self.gf('django.db.models.fields.CharField')(default=u'2', max_length=1)),
        ))
        db.send_create_signal('mailer', ['Message'])

        # Adding model 'DontSendEntry'
        db.create_table('mailer_dontsendentry', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('to_address', self.gf('django.db.models.fields.EmailField')(max_length=75)),
            ('when_added', self.gf('django.db.models.fields.DateTimeField')()),
        ))
        db.send_create_signal('mailer', ['DontSendEntry'])

        # Adding model 'MessageLog'
        db.create_table('mailer_messagelog', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('message_data', self.gf('django.db.models.fields.TextField')()),
            ('when_added', self.gf('django.db.models.fields.DateTimeField')(db_index=True)),
            ('priority', self.gf('django.db.models.fields.CharField')(max_length=1, db_index=True)),
            ('when_attempted', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('result', self.gf('django.db.models.fields.CharField')(max_length=1)),
            ('log_message', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('mailer', ['MessageLog'])


    def backwards(self, orm):
        # Deleting model 'Message'
        db.delete_table('mailer_message')

        # Deleting model 'DontSendEntry'
        db.delete_table('mailer_dontsendentry')

        # Deleting model 'MessageLog'
        db.delete_table('mailer_messagelog')


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