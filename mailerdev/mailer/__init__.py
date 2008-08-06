from django.utils.encoding import force_unicode
from django.conf import settings
from mailer.models import Message

# replacement for django.core.mail.send_mail

def send_mail(subject, message, from_address, to_addresses):

    # need to do this in case subject used lazy version of ugettext
    subject = force_unicode(subject)

    for to_address in to_addresses:
        Message(to_address=to_address, from_address=from_address, subject=subject, message_body=message).save()

def mail_admins(subject, message, fail_silently=False):
    for name, to_address in settings.ADMINS:
        Message(to_address=to_address,
                from_address=settings.SERVER_EMAIL,
                subject=settings.EMAIL_SUBJECT_PREFIX + force_unicode(subject),
                message_body=message).save()

if getattr(settings, 'MAILER_FOR_CHASH_EMAILS', False):
    from django.core.handlers import base
    base.mail_admins = mail_admins
