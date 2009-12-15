VERSION = (0, 2, 0, "dev", 1)

def get_version():
    if VERSION[3] == "final":
        return "%s.%s.%s" % (VERSION[0], VERSION[1], VERSION[2])
    elif VERSION[3] == "dev":
        return "%s.%s.%s%s%s" % (VERSION[0], VERSION[1], VERSION[2], VERSION[3], VERSION[4])
    else:
        return "%s.%s.%s%s" % (VERSION[0], VERSION[1], VERSION[2], VERSION[3])

__version__ = get_version()


PRIORITY_MAPPING = {
    "high": "1",
    "medium": "2",
    "low": "3",
    "deferred": "4",
}


# replacement for django.core.mail.send_mail


def send_mail(subject, message, from_email, recipient_list, priority="medium",
              fail_silently=False, auth_user=None, auth_password=None):
    from django.utils.encoding import force_unicode
    from mailer.models import Message
    
    priority = PRIORITY_MAPPING[priority]
    
    # need to do this in case subject used lazy version of ugettext
    subject = force_unicode(subject)
    message = force_unicode(message)
    
    if len(subject) > 100:
        subject = u"%s..." % subject[:97]
    
    for to_address in recipient_list:
        Message(to_address=to_address,
                from_address=from_email,
                subject=subject,
                message_body=message,
                priority=priority).save()


def send_html_mail(subject, message, message_html, from_email, recipient_list,
                   priority="medium", fail_silently=False, auth_user=None,
                   auth_password=None):
    """
    Function to queue HTML e-mails
    """
    from django.utils.encoding import force_unicode
    from mailer.models import Message
    
    priority = PRIORITY_MAPPING[priority]
    
    # need to do this in case subject used lazy version of ugettext
    subject = force_unicode(subject)
    
    for to_address in recipient_list:
        Message(to_address=to_address,
                from_address=from_email,
                subject=subject,
                message_body=message,
                message_body_html=message_html,
                priority=priority).save()


def mail_admins(subject, message, fail_silently=False, priority="medium"):
    from django.utils.encoding import force_unicode
    from django.conf import settings
    from mailer.models import Message
    
    priority = PRIORITY_MAPPING[priority]
    
    subject = settings.EMAIL_SUBJECT_PREFIX + force_unicode(subject)
    message = force_unicode(message)
    
    if len(subject) > 100:
        subject = u"%s..." % subject[:97]
    
    for name, to_address in settings.ADMINS:
        Message(to_address=to_address,
                from_address=settings.SERVER_EMAIL,
                subject=subject,
                message_body=message,
                priority=priority).save()


def mail_managers(subject, message, fail_silently=False, priority="medium"):
    from django.utils.encoding import force_unicode
    from django.conf import settings
    from mailer.models import Message
    
    priority = PRIORITY_MAPPING[priority]
    
    subject = settings.EMAIL_SUBJECT_PREFIX + force_unicode(subject)
    message = force_unicode(message)
    
    if len(subject) > 100:
        subject = u"%s..." % subject[:97]
    
    for name, to_address in settings.MANAGERS:
        Message(to_address=to_address,
                from_address=settings.SERVER_EMAIL,
                subject=subject,
                message_body=message,
                priority=priority).save()
