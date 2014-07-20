from django.core.mail.backends.base import BaseEmailBackend

from mailer.models import Message


class DbBackend(BaseEmailBackend):

    def send_messages(self, email_messages):
        num_sent = 0
        for email in email_messages:
            msg = Message()
            msg.email = email
            msg.save()
            num_sent += 1
        return num_sent
