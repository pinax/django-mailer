from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail import get_connection

from django.conf import settings

from mailer.models import Message

BACKUP_BACKEND_NAME = getattr(settings, 'MAILER_BACKUP_BACKEND', None)
if BACKUP_BACKEND_NAME:
    BACKUP_BACKEND = get_connection(BACKUP_BACKEND_NAME)
else:
    BACKUP_BACKEND = None

class DbBackend(BaseEmailBackend):

    def send_messages(self, email_messages):
        try:
            num_sent = 0
            for email in email_messages:
                msg = Message()
                msg.email = email
                msg.save()
                num_sent += 1
            return num_sent
        except Exception, e:
            if BACKUP_BACKEND:
                return BACKUP_BACKEND.send_messages(email_messages)
            else:
                raise
