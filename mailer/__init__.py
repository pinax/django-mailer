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
    from mailer.models import make_message
    
    priority = PRIORITY_MAPPING[priority]
    
    # need to do this in case subject used lazy version of ugettext
    subject = force_unicode(subject)
    message = force_unicode(message)
    
    make_message(subject=subject,
                 body=message,
                 from_email=from_email,
                 to=recipient_list,
                 priority=priority).save()
    return 1


def send_html_mail(subject, message, message_html, from_email, recipient_list,
                   priority="medium", fail_silently=False, auth_user=None,
                   auth_password=None):
    """
    Function to queue HTML e-mails
    """
    from django.utils.encoding import force_unicode
    from django.core.mail import EmailMultiAlternatives
    from mailer.models import make_message
    
    priority = PRIORITY_MAPPING[priority]
    
    # need to do this in case subject used lazy version of ugettext
    subject = force_unicode(subject)
    message = force_unicode(message)
    
    msg = make_message(subject=subject,
                       body=message,
                       from_email=from_email,
                       to=recipient_list,
                       priority=priority)
    email = msg.email
    email = EmailMultiAlternatives(email.subject, email.body, email.from_email, email.to)
    email.attach_alternative(message_html, "text/html")
    msg.email = email
    msg.save()
    return 1


def mail_admins(subject, message, fail_silently=False, connection=None, priority="medium"):
    from django.conf import settings
    from django.utils.encoding import force_unicode

    return send_mail(settings.EMAIL_SUBJECT_PREFIX + force_unicode(subject),
                     message,
                     settings.SERVER_EMAIL,
                     [a[1] for a in settings.ADMINS])


def mail_managers(subject, message, fail_silently=False, connection=None, priority="medium"):
    from django.conf import settings
    from django.utils.encoding import force_unicode

    return send_mail(settings.EMAIL_SUBJECT_PREFIX + force_unicode(subject),
                     message,
                     settings.SERVER_EMAIL,
                     [a[1] for a in settings.MANAGERS])
