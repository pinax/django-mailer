from __future__ import absolute_import

import warnings

VERSION = (1, 2, 3, "alpha", 0)  # following PEP 386
DEV_N = None


def get_version():
    version = "%s.%s" % (VERSION[0], VERSION[1])
    if VERSION[2]:
        version = "%s.%s" % (version, VERSION[2])
    if VERSION[3] != "final":
        version = "%s%s%s" % (version, VERSION[3], VERSION[4])
        if DEV_N:
            version = "%s.dev%s" % (version, DEV_N)
    return version


__version__ = get_version()


def get_priority(priority):
    from mailer.models import PRIORITY_MAPPING, PRIORITY_MEDIUM
    if priority is None:
        priority = PRIORITY_MEDIUM

    if priority in PRIORITY_MAPPING:
        warnings.warn("Please pass one of the PRIORITY_* constants to 'send_mail' "
                      "and 'send_html_mail', not '{0}'.".format(priority),
                      DeprecationWarning)
        priority = PRIORITY_MAPPING[priority]
    if priority not in PRIORITY_MAPPING.values():
        raise ValueError("Invalid priority {0}".format(repr(priority)))
    return priority


# replacement for django.core.mail.send_mail

def send_mail(subject, message, from_email, recipient_list, priority=None,
              fail_silently=False, auth_user=None, auth_password=None):
    from django.utils.encoding import force_text
    from mailer.models import make_message

    priority = get_priority(priority)
    # need to do this in case subject used lazy version of ugettext
    subject = force_text(subject)
    message = force_text(message)

    make_message(subject=subject,
                 body=message,
                 from_email=from_email,
                 to=recipient_list,
                 priority=priority).save()
    return 1


def send_html_mail(subject, message, message_html, from_email, recipient_list,
                   priority=None, fail_silently=False, auth_user=None,
                   auth_password=None, headers={}):
    """
    Function to queue HTML e-mails
    """
    from django.utils.encoding import force_text
    from django.core.mail import EmailMultiAlternatives
    from mailer.models import make_message

    priority = get_priority(priority)

    # need to do this in case subject used lazy version of ugettext
    subject = force_text(subject)
    message = force_text(message)

    msg = make_message(subject=subject,
                       body=message,
                       from_email=from_email,
                       to=recipient_list,
                       priority=priority)
    email = msg.email
    email = EmailMultiAlternatives(
        email.subject,
        email.body,
        email.from_email,
        email.to,
        headers=headers
    )
    email.attach_alternative(message_html, "text/html")
    msg.email = email
    msg.save()
    return 1


def send_mass_mail(datatuple, fail_silently=False, auth_user=None,
                   auth_password=None, connection=None):
    num_sent = 0
    for subject, message, sender, recipient in datatuple:
        num_sent += send_mail(subject, message, sender, recipient)
    return num_sent


def mail_admins(subject, message, fail_silently=False, connection=None, priority=None):
    from django.conf import settings
    from django.utils.encoding import force_text

    return send_mail(settings.EMAIL_SUBJECT_PREFIX + force_text(subject),
                     message,
                     settings.SERVER_EMAIL,
                     [a[1] for a in settings.ADMINS])


def mail_managers(subject, message, fail_silently=False, connection=None, priority=None):
    from django.conf import settings
    from django.utils.encoding import force_text

    return send_mail(settings.EMAIL_SUBJECT_PREFIX + force_text(subject),
                     message,
                     settings.SERVER_EMAIL,
                     [a[1] for a in settings.MANAGERS])
