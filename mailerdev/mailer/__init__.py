from django.utils.encoding import force_unicode
from django.conf import settings

PRIORITY_MAPPING = {
    "high": "1",
    "medium": "2",
    "low": "3",
    "deferred": "4",
}

# replacement for django.core.mail.send_mail

def send_mail(subject, message, from_email, recipient_list, priority="medium",
              fail_silently=False, auth_user=None, auth_password=None):
    from mailer.models import Message
    # need to do this in case subject used lazy version of ugettext
    subject = force_unicode(subject)
    priority = PRIORITY_MAPPING[priority]
    for to_address in recipient_list:
        Message(to_address=to_address,
                from_address=from_email,
                subject=subject,
                message_body=message,
                priority=priority).save()

def mail_admins(subject, message, fail_silently=False, priority="medium"):
    from mailer.models import Message
    priority = PRIORITY_MAPPING[priority]
    for name, to_address in settings.ADMINS:
        Message(to_address=to_address,
                from_address=settings.SERVER_EMAIL,
                subject=settings.EMAIL_SUBJECT_PREFIX + force_unicode(subject),
                message_body=message,
                priority=priority).save()

if getattr(settings, 'MAILER_FOR_CRASH_EMAILS', False):
    from django.core.handlers import base
    base.mail_admins = mail_admins
