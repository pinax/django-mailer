from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail.backends.base import BaseEmailBackend

from mailer.models import Message


class DbBackend(BaseEmailBackend):
    def __init__(self, *args, using=None, **kwargs):
        super().__init__(*args, **kwargs)
        # "using" is the MAILERS alias that delivers the queued mail. It is read
        # from the settings by mailer.engine, so it is only checked here.
        self.using = using
        if getattr(self, "alias", None) is not None and using is None:
            raise ImproperlyConfigured(
                f'The "{self.alias}" mailer needs a "using" option that names the mailer which delivers queued mail'
            )

    def send_messages(self, email_messages):
        # allow for a custom batch size
        MESSAGES_BATCH_SIZE = getattr(settings, "MAILER_MESSAGES_BATCH_SIZE", None)

        messages = Message.objects.bulk_create([Message(email=email) for email in email_messages], MESSAGES_BATCH_SIZE)

        return len(messages)
