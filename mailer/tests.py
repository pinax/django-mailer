from django.test import TestCase
from django.core import mail
from django.core.mail.backends.locmem import EmailBackend as LocMemEmailBackend
from django.utils.timezone import now as datetime_now
from django.core.management import call_command

from mailer.models import (Message, MessageLog, DontSendEntry, Queue, db_to_email, email_to_db,
                           PRIORITY_HIGH, PRIORITY_MEDIUM, PRIORITY_LOW, PRIORITY_DEFERRED)
import mailer
from mailer import engine

from mock import patch, Mock, ANY
from time import strftime
import pickle
import lockfile
import smtplib
import time
import logging
import datetime

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
    fixtures = ['mailer_queue']
    def setUp(self):
        # Ensure outbox is empty at start
        del TestMailerEmailBackend.outbox[:]

    def test_mailer_email_backend(self):
        """
        Test that calling "manage.py send_mail" actually sends mail using the
        specified MAILER_EMAIL_BACKEND
        """
        with self.settings(MAILER_EMAIL_BACKEND="mailer.tests.TestMailerEmailBackend"):
            mailer.send_mail("Subject", "Body", "sender1@example.com", ["recipient@example.com"])
            self.assertEqual(Message.objects.count(), 1)
            self.assertEqual(len(TestMailerEmailBackend.outbox), 0)
            engine.send_all()
            self.assertEqual(len(TestMailerEmailBackend.outbox), 1)
            self.assertEqual(Message.objects.count(), 0)
            self.assertEqual(MessageLog.objects.count(), 1)

    def test_retry_deferred(self):
        with self.settings(MAILER_EMAIL_BACKEND="mailer.tests.FailingMailerEmailBackend"):
            mailer.send_mail("Subject", "Body", "sender2@example.com", ["recipient@example.com"])
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

                mailer.send_mail("Subject", "Body", "sender15@example.com", ["rec@example.com"])

                self.assertRaises(StopIteration, engine.send_loop)
                send.assert_called_once_with()

    def test_send_html(self):
        with self.settings(MAILER_EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"):
            mailer.send_html_mail("Subject", "Body", "<html><body>Body</body></html>",
                                  "htmlsender1@example.com", ["recipient@example.com"],
                                  priority=PRIORITY_HIGH)

            # Ensure deferred was not deleted
            self.assertEqual(Message.objects.count(), 1)
            self.assertEqual(Message.objects.deferred().count(), 0)

            engine.send_all()

            self.assertEqual(len(mail.outbox), 1)
            sent = mail.outbox[0]

            # Default "plain text"
            self.assertEqual(sent.body, "Body")
            self.assertEqual(sent.content_subtype, "plain")

            # Alternative "text/html"
            self.assertEqual(sent.alternatives[0],
                             ("<html><body>Body</body></html>", "text/html"))

    def test_send_mass_mail(self):
        with self.settings(MAILER_EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"):
            mails = (
                ("Subject", "Body", "mass0@example.com", ["recipient0@example.com"]),
                ("Subject", "Body", "mass1@example.com", ["recipient1@example.com"]),
                ("Subject", "Body", "mass2@example.com", ["recipient2@example.com"]),
                ("Subject", "Body", "mass3@example.com", ["recipient3@example.com"]),
            )

            mailer.send_mass_mail(mails)

            self.assertEqual(Message.objects.count(), 4)
            self.assertEqual(Message.objects.deferred().count(), 0)

            engine.send_all()

            self.assertEqual(Message.objects.count(), 0)
            self.assertEqual(Message.objects.deferred().count(), 0)

            self.assertEqual(len(mail.outbox), 4)
            for i, sent in enumerate(mail.outbox):
                # Default "plain text"
                self.assertEqual(sent.from_email, "mass{0}@example.com".format(i))
                self.assertEqual(sent.to, ["recipient{0}@example.com".format(i)])

    def test_mail_admins(self):
        with self.settings(MAILER_EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", ADMINS=(("Test", "testadmin@example.com"),)):  # noqa
            mailer.mail_admins("Subject", "Admin Body")

            self.assertEqual(Message.objects.count(), 1)
            self.assertEqual(Message.objects.deferred().count(), 0)

            engine.send_all()

            self.assertEqual(Message.objects.count(), 0)
            self.assertEqual(Message.objects.deferred().count(), 0)

            self.assertEqual(len(mail.outbox), 1)
            sent = mail.outbox[0]

            # Default "plain text"
            self.assertEqual(sent.body, "Admin Body")
            self.assertEqual(sent.to, ["testadmin@example.com"])

    def test_mail_managers(self):
        with self.settings(MAILER_EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", MANAGERS=(("Test", "testmanager@example.com"),)):  # noqa
            mailer.mail_managers("Subject", "Manager Body")

            self.assertEqual(Message.objects.count(), 1)
            self.assertEqual(Message.objects.deferred().count(), 0)

            engine.send_all()

            self.assertEqual(Message.objects.count(), 0)
            self.assertEqual(Message.objects.deferred().count(), 0)

            self.assertEqual(len(mail.outbox), 1)
            sent = mail.outbox[0]

            # Default "plain text"
            self.assertEqual(sent.body, "Manager Body")
            self.assertEqual(sent.to, ["testmanager@example.com"])

    def test_blacklisted_emails(self):
        with self.settings(MAILER_EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"):
            now = datetime_now()
            obj = DontSendEntry.objects.create(to_address="nogo@example.com", when_added=now)
            self.assertTrue(obj.to_address, "nogo@example.com")

            mailer.send_mail("Subject", "GoBody", "send1@example.com", ["go@example.com"])
            mailer.send_mail("Subject", "NoGoBody", "send2@example.com", ["nogo@example.com"])

            self.assertEqual(Message.objects.count(), 2)
            self.assertEqual(Message.objects.deferred().count(), 0)

            engine.send_all()

            # All messages are processed
            self.assertEqual(Message.objects.count(), 0)
            self.assertEqual(Message.objects.deferred().count(), 0)

            # but only one should get sent
            self.assertEqual(len(mail.outbox), 1)
            sent = mail.outbox[0]

            # Default "plain text"
            self.assertEqual(sent.body, "GoBody")
            self.assertEqual(sent.to, ["go@example.com"])

    def test_control_max_delivery_amount(self):
        with self.settings(MAILER_EMAIL_BACKEND="mailer.tests.TestMailerEmailBackend", MAILER_EMAIL_MAX_BATCH=2):  # noqa
            mailer.send_mail("Subject1", "Body1", "sender1@example.com", ["recipient1@example.com"])
            mailer.send_mail("Subject2", "Body2", "sender2@example.com", ["recipient2@example.com"])
            mailer.send_mail("Subject3", "Body3", "sender3@example.com", ["recipient3@example.com"])
            self.assertEqual(Message.objects.count(), 3)
            self.assertEqual(len(TestMailerEmailBackend.outbox), 0)
            engine.send_all()
            self.assertEqual(len(TestMailerEmailBackend.outbox), 2)
            self.assertEqual(Message.objects.count(), 1)
            self.assertEqual(MessageLog.objects.count(), 2)

    def test_control_max_retry_amount(self):
        with self.settings(MAILER_EMAIL_BACKEND="mailer.tests.TestMailerEmailBackend"):  # noqa
            # 5 normal emails scheduled for delivery
            mailer.send_mail("Subject1", "Body1", "sender1@example.com", ["recipient1@example.com"])
            mailer.send_mail("Subject2", "Body2", "sender2@example.com", ["recipient2@example.com"])
            mailer.send_mail("Subject3", "Body3", "sender3@example.com", ["recipient3@example.com"])
            mailer.send_mail("Subject4", "Body4", "sender4@example.com", ["recipient4@example.com"])
            mailer.send_mail("Subject5", "Body5", "sender5@example.com", ["recipient5@example.com"])
            self.assertEqual(Message.objects.count(), 5)
            self.assertEqual(Message.objects.deferred().count(), 0)

        with self.settings(MAILER_EMAIL_BACKEND="mailer.tests.FailingMailerEmailBackend", MAILER_EMAIL_MAX_DEFERRED=2):  # noqa
            # 2 will get deferred 3 remain undeferred
            with patch("logging.warning") as w:
                engine.send_all()

                w.assert_called_once_with(ANY, 2)
                # Possibly need a way of running the comparisons below
                # arg = w.call_args[0][0]
                # self.assertIn("EMAIL_MAX_DEFERRED", arg)
                # self.assertIn("stopping for this round", arg)

            self.assertEqual(Message.objects.count(), 5)
            self.assertEqual(Message.objects.deferred().count(), 2)

        with self.settings(MAILER_EMAIL_BACKEND="mailer.tests.TestMailerEmailBackend", MAILER_EMAIL_MAX_DEFERRED=2):  # noqa
            # 3 will be delivered, 2 remain deferred
            engine.send_all()
            self.assertEqual(len(TestMailerEmailBackend.outbox), 3)
            # Should not have sent the deferred ones
            self.assertEqual(Message.objects.count(), 2)
            self.assertEqual(Message.objects.deferred().count(), 2)

            # Now mark them for retrying
            Message.objects.retry_deferred()
            engine.send_all()
            self.assertEqual(len(TestMailerEmailBackend.outbox), 2)
            self.assertEqual(Message.objects.count(), 0)

    def test_throttling_delivery(self):
        TIME = 1  # throttle time = 1 second

        with self.settings(MAILER_EMAIL_BACKEND="mailer.tests.TestMailerEmailBackend", MAILER_EMAIL_THROTTLE=TIME):  # noqa
            mailer.send_mail("Subject", "Body", "sender13@example.com", ["recipient@example.com"])
            mailer.send_mail("Subject", "Body", "sender14@example.com", ["recipient@example.com"])
            start_time = time.time()
            engine.send_all()
            throttled_time = time.time() - start_time

            self.assertEqual(len(TestMailerEmailBackend.outbox), 2)
            self.assertEqual(Message.objects.count(), 0)

        # Notes: 2 * TIME because 2 emails are sent during the test
        self.assertGreater(throttled_time, 2 * TIME)


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
        self.prio.assert_called_once_with()

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
    fixtures = ['mailer_queue']
    def test_prioritize(self):
        with self.settings(MAILER_EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"):
            mailer.send_mail("Subject", "Body", "prio1@example.com", ["r@example.com"],
                             priority=PRIORITY_HIGH)
            mailer.send_mail("Subject", "Body", "prio2@example.com", ["r@example.com"],
                             priority=PRIORITY_MEDIUM)
            mailer.send_mail("Subject", "Body", "prio3@example.com", ["r@example.com"],
                             priority=PRIORITY_LOW)
            mailer.send_mail("Subject", "Body", "prio4@example.com", ["r@example.com"],
                             priority=PRIORITY_HIGH)
            mailer.send_mail("Subject", "Body", "prio5@example.com", ["r@example.com"],
                             priority=PRIORITY_HIGH)
            mailer.send_mail("Subject", "Body", "prio6@example.com", ["r@example.com"],
                             priority=PRIORITY_LOW)
            mailer.send_mail("Subject", "Body", "prio7@example.com", ["r@example.com"],
                             priority=PRIORITY_LOW)
            mailer.send_mail("Subject", "Body", "prio8@example.com", ["r@example.com"],
                             priority=PRIORITY_MEDIUM)
            mailer.send_mail("Subject", "Body", "prio9@example.com", ["r@example.com"],
                             priority=PRIORITY_MEDIUM)
            mailer.send_mail("Subject", "Body", "prio10@example.com", ["r@example.com"],
                             priority=PRIORITY_LOW)
            mailer.send_mail("Subject", "Body", "prio11@example.com", ["r@example.com"],
                             priority=PRIORITY_MEDIUM)
            mailer.send_mail("Subject", "Body", "prio12@example.com", ["r@example.com"],
                             priority=PRIORITY_HIGH)
            mailer.send_mail("Subject", "Body", "prio13@example.com", ["r@example.com"],
                             priority=PRIORITY_DEFERRED)
            self.assertEqual(Message.objects.count(), 13)
            self.assertEqual(Message.objects.deferred().count(), 1)
            self.assertEqual(Message.objects.non_deferred().count(), 12)

            messages = engine.prioritize()

            # High priority
            msg = next(messages)
            self.assertEqual(msg.email.from_email, "prio1@example.com")
            msg.delete()
            msg = next(messages)
            self.assertEqual(msg.email.from_email, "prio4@example.com")
            msg.delete()
            msg = next(messages)
            self.assertEqual(msg.email.from_email, "prio5@example.com")
            msg.delete()
            msg = next(messages)
            self.assertEqual(msg.email.from_email, "prio12@example.com")
            msg.delete()

            # Medium priority
            msg = next(messages)
            self.assertEqual(msg.email.from_email, "prio2@example.com")
            msg.delete()
            msg = next(messages)
            self.assertEqual(msg.email.from_email, "prio8@example.com")
            msg.delete()
            msg = next(messages)
            self.assertEqual(msg.email.from_email, "prio9@example.com")
            msg.delete()
            msg = next(messages)
            self.assertEqual(msg.email.from_email, "prio11@example.com")
            msg.delete()

            # Low priority
            msg = next(messages)
            self.assertEqual(msg.email.from_email, "prio3@example.com")
            msg.delete()
            msg = next(messages)
            self.assertEqual(msg.email.from_email, "prio6@example.com")
            msg.delete()
            msg = next(messages)
            self.assertEqual(msg.email.from_email, "prio7@example.com")
            msg.delete()
            msg = next(messages)
            self.assertEqual(msg.email.from_email, "prio10@example.com")
            msg.delete()

            # Add one more mail that should still get delivered
            mailer.send_mail("Subject", "Body", "prio14@example.com", ["r@example.com"],
                             priority=PRIORITY_HIGH)
            msg = next(messages)
            self.assertEqual(msg.email.from_email, "prio14@example.com")
            msg.delete()

            # Ensure nothing else comes up
            self.assertRaises(StopIteration, lambda: next(messages))

            # Ensure deferred was not deleted
            self.assertEqual(Message.objects.count(), 1)
            self.assertEqual(Message.objects.deferred().count(), 1)


class TestMessages(TestCase):
    fixtures = ['mailer_queue']
    def test_message(self):
        with self.settings(MAILER_EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"):
            mailer.send_mail("Subject Msg", "Body", "msg1@example.com", ["rec1@example.com"])

            self.assertEqual(Message.objects.count(), 1)
            self.assertEqual(Message.objects.deferred().count(), 0)
            self.assertEqual(MessageLog.objects.count(), 0)

            msg = Message.objects.all()[0]

            self.assertEqual(msg.email.from_email, "msg1@example.com")
            self.assertEqual(msg.to_addresses, ["rec1@example.com"])
            self.assertEqual(msg.subject, "Subject Msg")

            # Fake a msg stored in DB with invalid data
            msg.message_data = ""

            self.assertEqual(msg.to_addresses, [])
            self.assertEqual(msg.subject, "")

            msg.save()

            with patch("logging.warning") as w:
                engine.send_all()

                w.assert_called_once_with(ANY)
                # Possibly need a way of running the comparisons below
                # arg = w.call_args[0][0]
                # self.assertIn("message discarded due to failure in converting from DB", arg)

            self.assertEqual(Message.objects.count(), 0)
            self.assertEqual(Message.objects.deferred().count(), 0)
            # Delivery should discard broken messages
            self.assertEqual(MessageLog.objects.count(), 0)

    def test_message_log(self):
        with self.settings(MAILER_EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"):
            mailer.send_mail("Subject Log", "Body", "log1@example.com", ["1gol@example.com"])

            self.assertEqual(Message.objects.count(), 1)
            self.assertEqual(Message.objects.deferred().count(), 0)
            self.assertEqual(MessageLog.objects.count(), 0)

            engine.send_all()

            self.assertEqual(Message.objects.count(), 0)
            self.assertEqual(Message.objects.deferred().count(), 0)
            self.assertEqual(MessageLog.objects.count(), 1)

            log = MessageLog.objects.all()[0]

            self.assertEqual(log.email.from_email, "log1@example.com")
            self.assertEqual(log.to_addresses, ["1gol@example.com"])
            self.assertEqual(log.subject, "Subject Log")

            # Fake a log entry without email
            log.message_data = ""

            self.assertEqual(log.to_addresses, [])
            self.assertEqual(log.subject, "")


class TestDbToEmail(TestCase):
    def test_db_to_email(self):
        # Empty/Invalid content
        self.assertEqual(db_to_email(""), None)
        self.assertEqual(db_to_email(None), None)

        # Other objects which should be returned as-is
        data = "Hello Email"
        self.assertEqual(db_to_email(email_to_db(data)), data)

        data = ["Test subject", "Test body", "testsender@example.com", ["testrec@example.com"]]
        self.assertEqual(db_to_email(email_to_db(data)), data)

        email = mail.EmailMessage(*data)
        converted_email = db_to_email(email_to_db(email))
        self.assertEqual(converted_email.body, email.body)
        self.assertEqual(converted_email.subject, email.subject)
        self.assertEqual(converted_email.from_email, email.from_email)
        self.assertEqual(converted_email.to, email.to)

        # Test old pickle in DB format
        db_email = pickle.dumps(email)
        converted_email = db_to_email(db_email)
        self.assertEqual(converted_email.body, email.body)
        self.assertEqual(converted_email.subject, email.subject)
        self.assertEqual(converted_email.from_email, email.from_email)
        self.assertEqual(converted_email.to, email.to)

class TestQueue(TestCase):
    fixtures = ['mailer_queue']
    def test_default_exist(self):
        # Check default queue exists
        self.assertEqual(Queue.objects.count(), 1)
        self.assertEqual(Queue.objects.get(pk=0).id, 0)

    def test_extra_queue(self):
        # Create extra queue
        q = Queue.objects.create(pk=1, name="test", mail_enabled=True)
        self.assertEqual(Queue.objects.count(), 2)

    def test_sending_extra_queue(self):
        # Put message in extra queue
        with self.settings(MAILER_EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"):
            q = Queue.objects.create(pk=1, name="test", mail_enabled=True)
            mailer.send_mail("Subject", "Body", "test@example.com", ["r@example.com"], queue=1)
            self.assertEqual(Queue.objects.count(), 2)
            self.assertEqual(Message.objects.count(), 1)
            self.assertEqual(Message.objects.deferred().count(), 0)

            engine.send_all()

            self.assertEqual(Message.objects.count(), 0)
            self.assertEqual(Message.objects.deferred().count(), 0)
            self.assertEqual(MessageLog.objects.count(), 1)

    def test_sending_extra_queue_disabled(self):
        # Test messages don't get sent that are in a disabled queue
        with self.settings(MAILER_EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"):
            q = Queue.objects.create(pk=1, name="test", mail_enabled=False)

            mailer.send_mail("Subject", "Body", "test@example.com", ["r@example.com"], queue=1)
            self.assertEqual(Message.objects.count(), 1)
            self.assertEqual(Message.objects.deferred().count(), 0)

            engine.send_all()

            self.assertEqual(Message.objects.count(), 1)
            self.assertEqual(Message.objects.deferred().count(), 1)
            self.assertEqual(MessageLog.objects.count(), 0)

    def test_multiple_queues(self):
        # Test sending on both an enabled and a disabled queue, ensure only one gets sent
        with self.settings(MAILER_EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"):
            q = Queue.objects.create(pk=1, name="test", mail_enabled=False)
            q1 = Queue.objects.create(pk=2, name="test1", mail_enabled=True)

            mailer.send_mail("Subject", "Body", "test@example.com", ["r@example.com"], queue=1)
            self.assertEqual(Message.objects.count(), 1)
            self.assertEqual(Message.objects.filter(queue=q).count(), 1)

            mailer.send_mail("Subject", "Body", "test@example.com", ["r@example.com"], queue=2)
            self.assertEqual(Message.objects.count(), 2)
            self.assertEqual(Message.objects.filter(queue=q1).count(), 1)

            engine.send_all()

            self.assertEqual(Message.objects.count(), 1)
            self.assertEqual(Message.objects.deferred().count(), 1)
            self.assertEqual(MessageLog.objects.count(), 1)

    def test_resend(self):
        # Test resend enables queue
        with self.settings(MAILER_EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"):
            q = Queue.objects.create(pk=1, name="test", mail_enabled=False)
            q1 = Queue.objects.create(pk=2, name="test1", mail_enabled=True)

            mailer.send_mail("Subject", "Body", "test@example.com", ["r@example.com"], queue=1)
            self.assertEqual(Message.objects.count(), 1)
            self.assertEqual(Message.objects.filter(queue=q).count(), 1)

            mailer.send_mail("Subject", "Body", "test@example.com", ["r@example.com"], queue=2)
            self.assertEqual(Message.objects.count(), 2)
            self.assertEqual(Message.objects.filter(queue=q1).count(), 1)

            engine.send_all()

            self.assertEqual(Message.objects.count(), 1)
            self.assertEqual(Message.objects.deferred().count(), 1)
            self.assertEqual(MessageLog.objects.count(), 1)

            date = datetime.datetime.now() - datetime.timedelta(minutes=15)
            engine.resend(['test'], date.strftime("%Y-%m-%d %H:%M"))

            q = Queue.objects.get(pk=1)

            self.assertEqual(q.mail_enabled, True)
            self.assertEqual(Message.objects.count(), 1)
            self.assertEqual(Message.objects.filter(queue=q).count(), 1)
            self.assertEqual(Message.objects.deferred().count(), 0)

    def test_resend_split_time(self):
        # Test resend enables queue and only sends message after specific time
        with self.settings(MAILER_EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"):
            q = Queue.objects.create(pk=1, name="test", mail_enabled=True)
            q1 = Queue.objects.create(pk=2, name="test1", mail_enabled=False)

            mailer.send_mail("Subject", "Body", "test@example.com", ["r@example.com"], queue=2)
            self.assertEqual(Message.objects.count(), 1)
            self.assertEqual(Message.objects.filter(queue=q1).count(), 1)

            mailer.send_mail("Subject", "Body", "test@example.com", ["r1@example.com"], queue=2)
            self.assertEqual(Message.objects.count(), 2)
            self.assertEqual(Message.objects.filter(queue=q1).count(), 2)

            message = Message.objects.get(pk=2)
            message.when_added = datetime.datetime.now() - datetime.timedelta(minutes=20)
            message.save()

            mailer.send_mail("Subject", "Body", "test1@example.com", ["r2@example.com"], queue=1)
            self.assertEqual(Message.objects.count(), 3)
            self.assertEqual(Message.objects.filter(queue=q1).count(), 2)

            engine.send_all()

            self.assertEqual(Message.objects.count(), 2)
            self.assertEqual(Message.objects.deferred().count(), 2)
            self.assertEqual(MessageLog.objects.count(), 1)

            date = datetime.datetime.now() - datetime.timedelta(minutes=15)
            engine.resend(['test1'], date.strftime("%Y-%m-%d %H:%M"))

            q = Queue.objects.get(pk=2)

            self.assertEqual(q.mail_enabled, True)
            self.assertEqual(Message.objects.count(), 2)
            self.assertEqual(Message.objects.filter(queue=q).count(), 2)
            self.assertEqual(Message.objects.deferred().count(), 1)
            self.assertEqual(Message.objects.deferred()[0].to_addresses, ["r1@example.com"])

    def test_resend_no_time(self):
        # Test resend renables queue with no time option
        with self.settings(MAILER_EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"):
            q = Queue.objects.create(pk=1, name="test", mail_enabled=False)
            q1 = Queue.objects.create(pk=2, name="test1", mail_enabled=False)

            mailer.send_mail("Subject", "Body", "test@example.com", ["r@example.com"], queue=2)
            self.assertEqual(Message.objects.count(), 1)
            self.assertEqual(Message.objects.filter(queue=q1).count(), 1)

            mailer.send_mail("Subject", "Body", "test@example.com", ["r1@example.com"], queue=2)
            self.assertEqual(Message.objects.count(), 2)
            self.assertEqual(Message.objects.filter(queue=q1).count(), 2)

            engine.send_all()

            self.assertEqual(Message.objects.count(), 2)
            self.assertEqual(Message.objects.deferred().count(), 2)

            engine.resend(['test', 'test1'])

            self.assertEqual(Message.objects.deferred().count(), 2)
            self.assertEqual(Message.objects.count(), 2)

    def test_resend_no_queue_found(self):
        # Test queue not found on resend
        with self.settings(MAILER_EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"):
            res = mailer.send_mail('sub', 'body', 'test@example.com', ['r1@example.com'], queue=1)
            self.assertEqual(res, 0)
        with patch('logging.warning') as warn:
            engine.resend(['notest'])
            warn.assert_called_once_with('Queue notest not found')


class TestCommands(TestCase):
    fixtures = ['mailer_queue']
    def test_resend_queue(self):
        q = Queue.objects.get(pk=0)
        q.mail_enabled = False
        q.save()

        self.assertEqual(q.mail_enabled, False)
        call_command('resend_queue', 'default')

        q = Queue.objects.get(pk=0)
        self.assertEqual(q.mail_enabled, True)

    def test_retry_deferred(self):
        with self.settings(MAILER_EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"):
            q = Queue.objects.get(pk=0)
            q.mail_enabled = False
            q.save()

            mailer.send_mail("Subject", "Body", "test@example.com", ["r1@example.com"], queue=0)

            engine.send_all()

            self.assertEqual(Message.objects.deferred().count(), 1)

            q.mail_enabled = True
            q.save()

            call_command('retry_deferred')

            self.assertEqual(Message.objects.deferred().count(), 0)

    def test_send_mail(self):
        call_command('send_mail')

class TestSpamLimiting(TestCase):
    fixtures = ['mailer_queue']

    def test_spam_limit(self):
        for x in range(0, 40):
            mailer.send_mail("Subject", "Body", "test@example.com", ["r"+str(x)+"@example.com"], queue=0)

        self.assertEqual(Message.objects.count(), 40)

        engine.send_all_with_checks()

        self.assertEqual(Message.objects.deferred().count(), 40)
        self.assertEqual(Message.objects.count(), 40)

    def test_spam_limit_multiple_queues(self):
        with self.settings(MAILER_EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"):
            for x in range(0,40):
                mailer.send_mail("Subject", "Body", "test@example.com", ["r"+str(x)+"@example.com"], queue=0)

            self.assertEqual(Message.objects.count(), 40)

            Queue.objects.create(name="test", mail_enabled=True, metadata="{\"limits\":{\"weekday\": 10, \"weekend\": 10, \"age\": 1}}")

            self.assertEqual(Queue.objects.count(), 2)

            mailer.send_mail("Subject", "Body", "test@example.com", ["r1@example.com"], queue=1)
            self.assertEqual(Message.objects.count(), 41)
            self.assertEqual(Message.objects.deferred().count(), 0)
            self.assertEqual(Message.objects.filter(queue=Queue.objects.get(pk=1)).count(), 1)
            self.assertEqual(Message.objects.filter(queue=Queue.objects.get(pk=0)).count(), 40)

            engine.send_all_with_checks()

            self.assertEqual(Message.objects.count(), 40)
            self.assertEqual(Message.objects.deferred().count(), 40)

    def test_max_age(self):
        with self.settings(MAILER_EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"):
            mailer.send_mail("Subject", "Body", "test@example.com", ["r@example.com"], queue=0)
            message = Message.objects.get(pk=1)
            message.when_added = datetime.datetime.now() - datetime.timedelta(hours = 3)
            message.save()

            engine.send_all_with_checks()

            self.assertEqual(Message.objects.deferred().count(), 1)
            self.assertEqual(Message.objects.count(), 1)

class TestMessageMetaData(TestCase):
    fixtures = ['mailer_queue']

    def test_set_metadata(self):
        mailer.send_mail("Subject", "Body", "test@example.com", ["r@example.com"], queue=0)
        message = Message.objects.get(pk=1)
        self.assertEqual(message.metadata, "{}")

        mailer.send_mail("Subject", "Body", "test@example.com", ["r@example.com"], queue=0, metadata={"test": "testval"})
        message = Message.objects.get(pk=2)
        self.assertEqual(message.metadata, "{'test': 'testval'}")
