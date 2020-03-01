import smtplib
from django.core.mail.backends.locmem import EmailBackend as LocMemEmailBackend


class FakeConnection(object):
    def __getstate__(self):
        raise TypeError("Connections can't be pickled")


class TestMailerEmailBackend(object):
    outbox = []

    def __init__(self, **kwargs):
        self.connection = FakeConnection()
        del self.outbox[:]

    def open(self):
        pass

    def close(self):
        pass

    def send_messages(self, email_messages):
        for m in email_messages:
            m.extra_headers['X-Sent-By'] = 'django-mailer-tests'
        self.outbox.extend(email_messages)


class FailingMailerEmailBackend(LocMemEmailBackend):
    def send_messages(self, email_messages):
        raise smtplib.SMTPSenderRefused(1, "foo", "foo@foo.com")
