from __future__ import unicode_literals

import base64
import logging
import pickle
import datetime

from django.utils.encoding import python_2_unicode_compatible
from django.utils.timezone import now as datetime_now
from django.core.mail import EmailMessage
from django.db import models
from django.utils.translation import ugettext_lazy as _


PRIORITY_HIGH = "1"
PRIORITY_MEDIUM = "2"
PRIORITY_LOW = "3"
PRIORITY_DEFERRED = "4"

PRIORITIES = [
    (PRIORITY_HIGH, "high"),
    (PRIORITY_MEDIUM, "medium"),
    (PRIORITY_LOW, "low"),
    (PRIORITY_DEFERRED, "deferred"),
]

PRIORITY_MAPPING = dict((label, v) for (v, label) in PRIORITIES)


def get_message_id(msg):
    # From django.core.mail.message: Email header names are case-insensitive
    # (RFC 2045), so we have to accommodate that when doing comparisons.
    for key, value in msg.extra_headers.items():
        if key.lower() == 'message-id':
            return value


class MessageManager(models.Manager):

    def high_priority(self):
        """
        the high priority messages in the queue
        """
        return self.filter(priority=PRIORITY_HIGH)

    def medium_priority(self):
        """
        the medium priority messages in the queue
        """
        return self.filter(priority=PRIORITY_MEDIUM)

    def low_priority(self):
        """
        the low priority messages in the queue
        """
        return self.filter(priority=PRIORITY_LOW)

    def non_deferred(self):
        """
        the messages in the queue not deferred
        """
        return self.exclude(priority=PRIORITY_DEFERRED)

    def deferred(self):
        """
        the deferred messages in the queue
        """
        return self.filter(priority=PRIORITY_DEFERRED)

    def retry_deferred(self, new_priority=PRIORITY_MEDIUM):
        count = 0
        for message in self.deferred():
            if message.retry(new_priority):
                count += 1
        return count


base64_encode = base64.encodebytes if hasattr(base64, 'encodebytes') else base64.encodestring
base64_decode = base64.decodebytes if hasattr(base64, 'decodebytes') else base64.decodestring


def email_to_db(email):
    # pickle.dumps returns essentially binary data which we need to encode
    # to store in a unicode field.
    return base64_encode(pickle.dumps(email))


def db_to_email(data):
    if data == "":
        return None
    else:
        try:
            data = data.encode("ascii")
        except AttributeError:
            pass

        try:
            return pickle.loads(base64_decode(data))
        except (TypeError, pickle.UnpicklingError, base64.binascii.Error, AttributeError):
            try:
                # previous method was to just do pickle.dumps(val)
                return pickle.loads(data)
            except (TypeError, pickle.UnpicklingError, AttributeError):
                return None


@python_2_unicode_compatible
class Message(models.Model):

    # The actual data - a pickled EmailMessage
    message_data = models.TextField()
    when_added = models.DateTimeField(default=datetime_now)
    priority = models.CharField(max_length=1, choices=PRIORITIES, default=PRIORITY_MEDIUM)
    # @@@ campaign?
    # @@@ content_type?

    objects = MessageManager()

    class Meta:
        verbose_name = _("message")
        verbose_name_plural = _("messages")

    def __str__(self):
        try:
            email = self.email
            return "On {0}, \"{1}\" to {2}".format(self.when_added,
                                                   email.subject,
                                                   ", ".join(email.to))
        except Exception:
            return "<Message repr unavailable>"

    def defer(self):
        self.priority = PRIORITY_DEFERRED
        self.save()

    def retry(self, new_priority=PRIORITY_MEDIUM):
        if self.priority == PRIORITY_DEFERRED:
            self.priority = new_priority
            self.save()
            return True
        else:
            return False

    def _get_email(self):
        return db_to_email(self.message_data)

    def _set_email(self, val):
        self.message_data = email_to_db(val)

    email = property(
        _get_email,
        _set_email,
        doc="""EmailMessage object. If this is mutated, you will need to
set the attribute again to cause the underlying serialised data to be updated.""")

    @property
    def to_addresses(self):
        email = self.email
        if email is not None:
            return email.to
        else:
            return []

    @property
    def subject(self):
        email = self.email
        if email is not None:
            return email.subject
        else:
            return ""


def filter_recipient_list(lst):
    if lst is None:
        return None
    retval = []
    for e in lst:
        if DontSendEntry.objects.has_address(e):
            logging.info("skipping email to %s as on don't send list " % e.encode("utf-8"))
        else:
            retval.append(e)
    return retval


def make_message(subject="", body="", from_email=None, to=None, bcc=None,
                 attachments=None, headers=None, priority=None):
    """
    Creates a simple message for the email parameters supplied.
    The 'to' and 'bcc' lists are filtered using DontSendEntry.

    If needed, the 'email' attribute can be set to any instance of EmailMessage
    if e-mails with attachments etc. need to be supported.

    Call 'save()' on the result when it is ready to be sent, and not before.
    """
    to = filter_recipient_list(to)
    bcc = filter_recipient_list(bcc)
    core_msg = EmailMessage(
        subject=subject,
        body=body,
        from_email=from_email,
        to=to,
        bcc=bcc,
        attachments=attachments,
        headers=headers
    )
    db_msg = Message(priority=priority)
    db_msg.email = core_msg
    return db_msg


class DontSendEntryManager(models.Manager):

    def has_address(self, address):
        """
        is the given address on the don't send list?
        """
        queryset = self.filter(to_address__iexact=address)
        return queryset.exists()


class DontSendEntry(models.Model):

    to_address = models.EmailField(max_length=254)
    when_added = models.DateTimeField()
    # @@@ who added?
    # @@@ comment field?

    objects = DontSendEntryManager()

    class Meta:
        verbose_name = _("don't send entry")
        verbose_name_plural = _("don't send entries")


RESULT_SUCCESS = "1"
RESULT_DONT_SEND = "2"
RESULT_FAILURE = "3"

RESULT_CODES = (
    (RESULT_SUCCESS, "success"),
    (RESULT_DONT_SEND, "don't send"),
    (RESULT_FAILURE, "failure"),
    # @@@ other types of failure?
)


class MessageLogManager(models.Manager):

    def log(self, message, result_code, log_message=""):
        """
        create a log entry for an attempt to send the given message and
        record the given result and (optionally) a log message
        """
        return self.create(
            message_data=message.message_data,
            message_id=get_message_id(message.email),
            when_added=message.when_added,
            priority=message.priority,
            # @@@ other fields from Message
            result=result_code,
            log_message=log_message,
        )

    def purge_old_entries(self, days):
        limit = datetime_now() - datetime.timedelta(days=days)
        query = self.filter(when_attempted__lt=limit, result=RESULT_SUCCESS)
        count = query.count()
        query.delete()
        return count


@python_2_unicode_compatible
class MessageLog(models.Model):

    # fields from Message
    message_data = models.TextField()
    message_id = models.TextField(editable=False, null=True)
    when_added = models.DateTimeField(db_index=True)
    priority = models.CharField(max_length=1, choices=PRIORITIES, db_index=True)
    # @@@ campaign?

    # additional logging fields
    when_attempted = models.DateTimeField(default=datetime_now)
    result = models.CharField(max_length=1, choices=RESULT_CODES)
    log_message = models.TextField()

    objects = MessageLogManager()

    class Meta:
        verbose_name = _("message log")
        verbose_name_plural = _("message logs")

    def __str__(self):
        try:
            email = self.email
            return "On {0}, \"{1}\" to {2}".format(self.when_attempted,
                                                   email.subject,
                                                   ", ".join(email.to))
        except Exception:
            return "<MessageLog repr unavailable>"

    @property
    def email(self):
        return db_to_email(self.message_data)

    @property
    def to_addresses(self):
        email = self.email
        if email is not None:
            return email.to
        else:
            return []

    @property
    def subject(self):
        email = self.email
        if email is not None:
            return email.subject
        else:
            return ""
