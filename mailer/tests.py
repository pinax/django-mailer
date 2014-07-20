from django.test import TestCase

from mailer.models import Message, MessageLog
from mailer.engine import send_all

import smtplib

sent_messages = []


class TestMailerEmailBackend(object):
    def __init__(self, **kwargs):
        global sent_messages
        sent_messages = []

    def open(self):
        pass

    def close(self):
        pass

    def send_messages(self, email_messages):
        global sent_messages
        sent_messages.extend(email_messages)


class FailingMailerEmailBackend(TestMailerEmailBackend):
    def send_messages(self, email_messages):
        raise smtplib.SMTPSenderRefused(1, "foo", "foo@foo.com")


class TestBackend(TestCase):

    def test_save_to_db(self):
        """
        Test that using send_mail creates a Message object in DB instead, when EMAIL_BACKEND is set.
        """
        from django.core.mail import send_mail
        self.assertEqual(Message.objects.count(), 0)
        with self.settings(EMAIL_BACKEND="mailer.backend.DbBackend"):
            send_mail("Subject", "Body", "sender@example.com", ["recipient@example.com"])
            self.assertEqual(Message.objects.count(), 1)


class TestSending(TestCase):
    def test_mailer_email_backend(self):
        """
        Test that calling "manage.py send_mail" actually sends mail using the
        specified MAILER_EMAIL_BACKEND
        """
        global sent_messages
        from mailer import send_mail
        with self.settings(MAILER_EMAIL_BACKEND="mailer.tests.TestMailerEmailBackend"):
            send_mail("Subject", "Body", "sender@example.com", ["recipient@example.com"])
            self.assertEqual(Message.objects.count(), 1)
            self.assertEqual(len(sent_messages), 0)
            from mailer.engine import send_all  # noqa
            send_all()
            self.assertEqual(len(sent_messages), 1)
            self.assertEqual(Message.objects.count(), 0)
            self.assertEqual(MessageLog.objects.count(), 1)

    def test_retry_deferred(self):
        global sent_messages
        from mailer import send_mail
        with self.settings(MAILER_EMAIL_BACKEND="mailer.tests.FailingMailerEmailBackend"):
            send_mail("Subject", "Body", "sender@example.com", ["recipient@example.com"])
            send_all()
            self.assertEqual(Message.objects.count(), 1)
            self.assertEqual(Message.objects.deferred().count(), 1)

        with self.settings(MAILER_EMAIL_BACKEND="mailer.tests.TestMailerEmailBackend"):
            send_all()
            self.assertEqual(len(sent_messages), 0)
            # Should not have sent the deferred ones
            self.assertEqual(Message.objects.count(), 1)
            self.assertEqual(Message.objects.deferred().count(), 1)

            # Now mark them for retrying
            Message.objects.retry_deferred()
            send_all()
            self.assertEqual(len(sent_messages), 1)
            self.assertEqual(Message.objects.count(), 0)
