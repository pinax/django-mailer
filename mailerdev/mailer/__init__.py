
from mailer.models import Message

# replacement for django.core.mail.send_mail

def send_mail(subject, message, from_address, to_addresses):
    for to_address in to_addresses:
        Message(to_address=to_address, from_address=from_address, subject=subject, message_body=message).save()
