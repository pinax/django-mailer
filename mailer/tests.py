from django.test import TestCase
from django.core import mail
from django.core.mail.backends.locmem import EmailBackend as LocMemEmailBackend

from mailer.models import Message, MessageLog
from mailer import send_mail as mailer_send_mail
from mailer import engine

from mock import patch, Mock
import lockfile
import smtplib


class TestMailerEmailBackend(object):
    outbox = []

    def __init__(self, **kwargs):
        del self.outbox[:]

    def open(self):
        pass

    def close(self):
        pass

    def send_messages(self, email_messages):
        self.outbox.extend(email_messages)


class FailingMailerEmailBackend(LocMemEmailBackend):
    def send_messages(self, email_messages):
        raise smtplib.SMTPSenderRefused(1, "foo", "foo@foo.com")


class TestBackend(TestCase):
    def test_save_to_db(self):
        """
        Test that using send_mail creates a Message object in DB instead, when EMAIL_BACKEND is set.
        """
        self.assertEqual(Message.objects.count(), 0)
        with self.settings(EMAIL_BACKEND="mailer.backend.DbBackend"):
            mail.send_mail("Subject", "Body", "sender@example.com", ["recipient@example.com"])
            self.assertEqual(Message.objects.count(), 1)


class TestSending(TestCase):
    def test_mailer_email_backend(self):
        """
        Test that calling "manage.py send_mail" actually sends mail using the
        specified MAILER_EMAIL_BACKEND
        """
        with self.settings(MAILER_EMAIL_BACKEND="mailer.tests.TestMailerEmailBackend"):
            mailer_send_mail("Subject", "Body", "sender1@example.com", ["recipient@example.com"])
            self.assertEqual(Message.objects.count(), 1)
            self.assertEqual(len(TestMailerEmailBackend.outbox), 0)
            engine.send_all()
            self.assertEqual(len(TestMailerEmailBackend.outbox), 1)
            self.assertEqual(Message.objects.count(), 0)
            self.assertEqual(MessageLog.objects.count(), 1)

    def test_retry_deferred(self):
        with self.settings(MAILER_EMAIL_BACKEND="mailer.tests.FailingMailerEmailBackend"):
            mailer_send_mail("Subject", "Body", "sender2@example.com", ["recipient@example.com"])
            engine.send_all()
            self.assertEqual(Message.objects.count(), 1)
            self.assertEqual(Message.objects.deferred().count(), 1)

        with self.settings(MAILER_EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"):

            engine.send_all()
            self.assertEqual(len(mail.outbox), 0)
            # Should not have sent the deferred ones
            self.assertEqual(Message.objects.count(), 1)
            self.assertEqual(Message.objects.deferred().count(), 1)

            # Now mark them for retrying
            Message.objects.retry_deferred()
            engine.send_all()
            self.assertEqual(len(mail.outbox), 1)
            self.assertEqual(Message.objects.count(), 0)

    def test_send_loop(self):
        with self.settings(MAILER_EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"):
            with patch("mailer.engine.send_all", side_effect=StopIteration) as send:
                with patch("time.sleep", side_effect=StopIteration) as sleep:
                    self.assertRaises(StopIteration, engine.send_loop)

                    sleep.assert_called_once_with(engine.EMPTY_QUEUE_SLEEP)
                    send.assert_not_called()

                mailer_send_mail("Subject", "Body", "sender15@example.com", ["recipient@example.com"])

                self.assertRaises(StopIteration, engine.send_loop)
                send.assert_called_once()


class TestLockNormal(TestCase):
    def setUp(self):
        class CustomError(Exception):
            pass

        self.CustomError = CustomError

        self.lock_mock = Mock()

        self.patcher_lock = patch("lockfile.FileLock", return_value=self.lock_mock)
        self.patcher_prio = patch("mailer.engine.prioritize", side_effect=CustomError)

        self.lock = self.patcher_lock.start()
        self.prio = self.patcher_prio.start()

    def test(self):
        self.assertRaises(self.CustomError, engine.send_all)
        self.lock_mock.acquire.assert_called_once_with(engine.LOCK_WAIT_TIMEOUT)
        self.lock.assert_called_once_with("send_mail")
        self.prio.assert_called_once()

    def tearDown(self):
        self.patcher_lock.stop()
        self.patcher_prio.stop()


class TestLockLocked(TestCase):
    def setUp(self):
        config = {
            "acquire.side_effect": lockfile.AlreadyLocked,
        }
        self.lock_mock = Mock(**config)

        self.patcher_lock = patch("lockfile.FileLock", return_value=self.lock_mock)
        self.patcher_prio = patch("mailer.engine.prioritize", side_effect=Exception)

        self.lock = self.patcher_lock.start()
        self.prio = self.patcher_prio.start()

    def test(self):
        engine.send_all()
        self.lock_mock.acquire.assert_called_once_with(engine.LOCK_WAIT_TIMEOUT)
        self.lock.assert_called_once_with("send_mail")
        self.prio.assert_not_called()

    def tearDown(self):
        self.patcher_lock.stop()
        self.patcher_prio.stop()


class TestLockTimeout(TestCase):
    def setUp(self):
        config = {
            "acquire.side_effect": lockfile.LockTimeout,
        }
        self.lock_mock = Mock(**config)

        self.patcher_lock = patch("lockfile.FileLock", return_value=self.lock_mock)
        self.patcher_prio = patch("mailer.engine.prioritize", side_effect=Exception)

        self.lock = self.patcher_lock.start()
        self.prio = self.patcher_prio.start()

    def test(self):
        engine.send_all()
        self.lock_mock.acquire.assert_called_once_with(engine.LOCK_WAIT_TIMEOUT)
        self.lock.assert_called_once_with("send_mail")
        self.prio.assert_not_called()

    def tearDown(self):
        self.patcher_lock.stop()
        self.patcher_prio.stop()


class TestPrioritize(TestCase):
    def test_prioritize(self):
        with self.settings(MAILER_EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"):
            # 5 normal emails scheduled for delivery
            mailer_send_mail("Subject", "Body", "prio1@example.com", ["recipient@example.com"], "high")
            mailer_send_mail("Subject", "Body", "prio2@example.com", ["recipient@example.com"], "medium")
            mailer_send_mail("Subject", "Body", "prio3@example.com", ["recipient@example.com"], "low")
            mailer_send_mail("Subject", "Body", "prio4@example.com", ["recipient@example.com"], "high")
            mailer_send_mail("Subject", "Body", "prio5@example.com", ["recipient@example.com"], "high")
            mailer_send_mail("Subject", "Body", "prio6@example.com", ["recipient@example.com"], "low")
            mailer_send_mail("Subject", "Body", "prio7@example.com", ["recipient@example.com"], "low")
            mailer_send_mail("Subject", "Body", "prio8@example.com", ["recipient@example.com"], "medium")
            mailer_send_mail("Subject", "Body", "prio9@example.com", ["recipient@example.com"], "medium")
            mailer_send_mail("Subject", "Body", "prio10@example.com", ["recipient@example.com"], "low")
            mailer_send_mail("Subject", "Body", "prio11@example.com", ["recipient@example.com"], "medium")
            mailer_send_mail("Subject", "Body", "prio12@example.com", ["recipient@example.com"], "high")
            mailer_send_mail("Subject", "Body", "prio13@example.com", ["recipient@example.com"], "deferred")
            self.assertEqual(Message.objects.count(), 13)
            self.assertEqual(Message.objects.deferred().count(), 1)

            messages = engine.prioritize()

            # High priority
            msg = messages.next()
            self.assertEqual(msg.email.from_email, "prio1@example.com")
            msg.delete()
            msg = messages.next()
            self.assertEqual(msg.email.from_email, "prio4@example.com")
            msg.delete()
            msg = messages.next()
            self.assertEqual(msg.email.from_email, "prio5@example.com")
            msg.delete()
            msg = messages.next()
            self.assertEqual(msg.email.from_email, "prio12@example.com")
            msg.delete()

            # Medium priority
            msg = messages.next()
            self.assertEqual(msg.email.from_email, "prio2@example.com")
            msg.delete()
            msg = messages.next()
            self.assertEqual(msg.email.from_email, "prio8@example.com")
            msg.delete()
            msg = messages.next()
            self.assertEqual(msg.email.from_email, "prio9@example.com")
            msg.delete()
            msg = messages.next()
            self.assertEqual(msg.email.from_email, "prio11@example.com")
            msg.delete()

            # Low priority
            msg = messages.next()
            self.assertEqual(msg.email.from_email, "prio3@example.com")
            msg.delete()
            msg = messages.next()
            self.assertEqual(msg.email.from_email, "prio6@example.com")
            msg.delete()
            msg = messages.next()
            self.assertEqual(msg.email.from_email, "prio7@example.com")
            msg.delete()
            msg = messages.next()
            self.assertEqual(msg.email.from_email, "prio10@example.com")
            msg.delete()

            # Add one more mail that should still get delivered
            mailer_send_mail("Subject", "Body", "prio14@example.com", ["recipient@example.com"], "high")
            msg = messages.next()
            self.assertEqual(msg.email.from_email, "prio14@example.com")
            msg.delete()

            # Ensure nothing else comes up
            self.assertRaises(StopIteration, messages.next)

            # Ensure deferred was not deleted
            self.assertEqual(Message.objects.count(), 1)
            self.assertEqual(Message.objects.deferred().count(), 1)
