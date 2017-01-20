# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime
import pickle
import smtplib
import time

import django
import lockfile
from django.core import mail
from django.core.mail.backends.locmem import EmailBackend as LocMemEmailBackend
from django.core.management import call_command
from django.test import TestCase
from django.utils import six
from django.utils.timezone import now as datetime_now
from mock import ANY, Mock, patch

import mailer
from mailer import engine
from mailer.models import (PRIORITY_DEFERRED, PRIORITY_HIGH, PRIORITY_LOW,
                           PRIORITY_MEDIUM, RESULT_FAILURE, RESULT_SUCCESS,
                           DontSendEntry, Message, MessageLog, db_to_email,
                           email_to_db, make_message)


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


class TestBackend(TestCase):
    def test_save_to_db(self):
        """
        Test that using send_mail creates a Message object in DB instead, when EMAIL_BACKEND is set.
        """
        self.assertEqual(Message.objects.count(), 0)
        with self.settings(EMAIL_BACKEND="mailer.backend.DbBackend"):
            mail.send_mail("Subject ☺", "Body", "sender@example.com", ["recipient@example.com"])
            self.assertEqual(Message.objects.count(), 1)


class TestSending(TestCase):
    def setUp(self):
        # Ensure outbox is empty at start
        del TestMailerEmailBackend.outbox[:]

    def test_mailer_email_backend(self):
        """
        Test that calling "manage.py send_mail" actually sends mail using the
        specified MAILER_EMAIL_BACKEND
        """
        with self.settings(MAILER_EMAIL_BACKEND="mailer.tests.TestMailerEmailBackend"):
            mailer.send_mail("Subject ☺", "Body", "sender1@example.com", ["recipient@example.com"])
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
            self.assertEqual(MessageLog.objects.count(), 1)

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

    def test_purge_old_entries(self):
        # Send one successfully
        with self.settings(MAILER_EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"):
            mailer.send_mail("Subject", "Body", "sender1@example.com",
                             ["recipient@example.com"])
            engine.send_all()

        # And one failure
        with self.settings(MAILER_EMAIL_BACKEND="mailer.tests.FailingMailerEmailBackend"):
            mailer.send_mail("Subject", "Body", "sender2@example.com",
                             ["recipient@example.com"])

            engine.send_all()
            Message.objects.retry_deferred()
            engine.send_all()

        with patch.object(mailer.models, 'datetime_now') as datetime_now_patch:
            datetime_now_patch.return_value = datetime_now() + datetime.timedelta(days=2)
            call_command('purge_mail_log', '1')

        self.assertNotEqual(MessageLog.objects.filter(result=RESULT_FAILURE).count(), 0)
        self.assertEqual(MessageLog.objects.filter(result=RESULT_SUCCESS).count(), 0)

    def test_send_loop(self):
        with self.settings(MAILER_EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"):
            with patch("mailer.engine.send_all", side_effect=StopIteration) as send:
                with patch("time.sleep", side_effect=StopIteration) as sleep:
                    self.assertRaises(StopIteration, engine.send_loop)

                    sleep.assert_called_once_with(engine.EMPTY_QUEUE_SLEEP)
                    send.assert_not_called()

                mailer.send_mail("Subject", "Body", "sender15@example.com", ["rec@example.com"])

                self.assertRaises(StopIteration, engine.send_loop)
                send.assert_called_once()

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
                ("Subject ☺", "Body", "mass0@example.com", ["recipient0@example.com"]),
                ("Subject ☺", "Body", "mass1@example.com", ["recipient1@example.com"]),
                ("Subject ☺", "Body", "mass2@example.com", ["recipient2@example.com"]),
                ("Subject ☺", "Body", "mass3@example.com", ["recipient3@example.com"]),
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
                self.assertEqual(sent.subject, "Subject ☺")
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

                w.assert_called_once()
                arg = w.call_args[0][0]
                self.assertIn("EMAIL_MAX_DEFERRED", arg)
                self.assertIn("stopping for this round", arg)

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

    def test_save_changes_to_email(self):
        """
        Test that changes made to the email by the backend are
        saved in MessageLog.
        """
        with self.settings(MAILER_EMAIL_BACKEND="mailer.tests.TestMailerEmailBackend"):
            mailer.send_mail("Subject", "Body", "sender@example.com", ["recipient@example.com"])
            engine.send_all()
            m = MessageLog.objects.get()
            self.assertEqual(m.email.extra_headers['X-Sent-By'],
                             'django-mailer-tests')

    def test_set_and_save_message_id(self):
        """
        Test that message-id is set and saved correctly
        """
        with self.settings(MAILER_EMAIL_BACKEND="mailer.tests.TestMailerEmailBackend"):
            mailer.send_mail("Subject", "Body", "sender@example.com", ["recipient@example.com"])
            engine.send_all()
            m = MessageLog.objects.get()
            self.assertEqual(
                m.email.extra_headers['Message-ID'],
                m.message_id
            )

    def test_save_existing_message_id(self):
        """
        Test that a preset message-id is saved correctly
        """
        with self.settings(MAILER_EMAIL_BACKEND="mailer.tests.TestMailerEmailBackend"):
            make_message(
                subject="Subject",
                body="Body",
                from_email="sender@example.com",
                to=["recipient@example.com"],
                priority=PRIORITY_MEDIUM,
                headers={'message-id': 'foo'},
            ).save()
            engine.send_all()
            m = MessageLog.objects.get()
            self.assertEqual(
                m.email.extra_headers['message-id'],
                'foo'
            )
            self.assertEqual(
                m.message_id,
                'foo'
            )


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

                w.assert_called_once()
                arg = w.call_args[0][0]
                self.assertIn("message discarded due to failure in converting from DB", arg)

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

    def test_message_str(self):
        with self.settings(MAILER_EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"):
            mailer.send_mail("Subject Msg 中", "Body 中", "msg1@example.com", ["rec1@example.com"])

            self.assertEqual(Message.objects.count(), 1)

            msg = Message.objects.get()
            self.assertEqual(
                six.text_type(msg),
                'On {0}, "Subject Msg 中" to rec1@example.com'.format(msg.when_added),
            )
            msg.message_data = None
            self.assertEqual(str(msg), '<Message repr unavailable>')

    def test_message_log_str(self):
        with self.settings(MAILER_EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"):
            mailer.send_mail("Subject Log 中", "Body 中", "log1@example.com", ["1gol@example.com"])
            engine.send_all()

            self.assertEqual(MessageLog.objects.count(), 1)

            log = MessageLog.objects.get()
            self.assertEqual(
                six.text_type(log),
                'On {0}, "Subject Log 中" to 1gol@example.com'.format(log.when_attempted),
            )

            log.message_data = None
            self.assertEqual(str(log), '<MessageLog repr unavailable>')


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


def call_command_with_cron_arg(command, cron_value):
    # for old django versions, `call_command` doesn't parse arguments
    if django.VERSION < (1, 8):
        return call_command(command, cron=cron_value)

    # newer django; test parsing by passing argument as string
    return call_command(command, '--cron={}'.format(cron_value))


class TestCommandHelper(TestCase):
    def test_send_mail_no_cron(self):
        with patch('mailer.management.commands.send_mail.logging') as logging:
            call_command('send_mail')
            logging.basicConfig.assert_called_with(level=logging.DEBUG, format=ANY)

    def test_send_mail_cron_0(self):
        with patch('mailer.management.commands.send_mail.logging') as logging:
            call_command_with_cron_arg('send_mail', 0)
            logging.basicConfig.assert_called_with(level=logging.DEBUG, format=ANY)

    def test_send_mail_cron_1(self):
        with patch('mailer.management.commands.send_mail.logging') as logging:
            call_command_with_cron_arg('send_mail', 1)
            logging.basicConfig.assert_called_with(level=logging.ERROR, format=ANY)

    def test_retry_deferred_no_cron(self):
        with patch('mailer.management.commands.retry_deferred.logging') as logging:
            call_command('retry_deferred')
            logging.basicConfig.assert_called_with(level=logging.DEBUG, format=ANY)

    def test_retry_deferred_cron_0(self):
        with patch('mailer.management.commands.retry_deferred.logging') as logging:
            call_command_with_cron_arg('retry_deferred', 0)
            logging.basicConfig.assert_called_with(level=logging.DEBUG, format=ANY)

    def test_retry_deferred_cron_1(self):
        with patch('mailer.management.commands.retry_deferred.logging') as logging:
            call_command_with_cron_arg('retry_deferred', 1)
            logging.basicConfig.assert_called_with(level=logging.ERROR, format=ANY)
