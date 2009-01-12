from django.conf import settings

if getattr(settings, 'MAILER_FOR_CRASH_EMAILS', False):
    from django.core.handlers import base
    base.mail_admins = mail_admins
