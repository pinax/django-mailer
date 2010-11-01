import base64
import logging
import pickle

from datetime import datetime

from django.core.mail import EmailMessage
from django.db import models


PRIORITIES = (
    ("1", "high"),
    ("2", "medium"),
    ("3", "low"),
    ("4", "deferred"),
)


class MessageManager(models.Manager):
    
    def high_priority(self):
        """
        the high priority messages in the queue
        """
        
        return self.filter(priority="1")
    
    def medium_priority(self):
        """
        the medium priority messages in the queue
        """
        
        return self.filter(priority="2")
    
    def low_priority(self):
        """
        the low priority messages in the queue
        """
        
        return self.filter(priority="3")
    
    def non_deferred(self):
        """
        the messages in the queue not deferred
        """
        
        return self.filter(priority__lt="4")
    
    def deferred(self):
        """
        the deferred messages in the queue
        """
    
        return self.filter(priority="4")
    
    def retry_deferred(self, new_priority=2):
        count = 0
        for message in self.deferred():
            if message.retry(new_priority):
                count += 1
        return count


def email_to_db(email):
    # pickle.dumps returns essentially binary data which we need to encode
    # to store in a unicode field.
    return base64.encodestring(pickle.dumps(email))


def db_to_email(data):
    if data == u"":
        return None
    else:
        try:
            return pickle.loads(base64.decodestring(data))
        except Exception:
            try:
                # previous method was to just do pickle.dumps(val)
                return pickle.loads(data.encode("ascii"))
            except Exception:
                return None


class Message(models.Model):
    
    # The actual data - a pickled EmailMessage
    message_data = models.TextField()
    when_added = models.DateTimeField(default=datetime.now)
    priority = models.CharField(max_length=1, choices=PRIORITIES, default="2")
    # @@@ campaign?
    # @@@ content_type?
    
    objects = MessageManager()
    
    def defer(self):
        self.priority = "4"
        self.save()
    
    def retry(self, new_priority=2):
        if self.priority == "4":
            self.priority = new_priority
            self.save()
            return True
        else:
            return False
    
    def _get_email(self):
        return db_to_email(self.message_data)
    
    def _set_email(self, val):
        self.message_data = email_to_db(val)

    email = property(_get_email, _set_email, doc=
                     """EmailMessage object. If this is mutated, you will need to
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
    core_msg = EmailMessage(subject=subject, body=body, from_email=from_email,
                            to=to, bcc=bcc, attachments=attachments, headers=headers)
    
    db_msg = Message(priority=priority)
    db_msg.email = core_msg
    return db_msg


class DontSendEntryManager(models.Manager):
    
    def has_address(self, address):
        """
        is the given address on the don't send list?
        """
        
        queryset = self.filter(to_address__iexact=address)
        try:
            # Django 1.2
            return queryset.exists()
        except AttributeError:
            # AttributeError: 'QuerySet' object has no attribute 'exists'
            return bool(queryset.count())


class DontSendEntry(models.Model):
    
    to_address = models.EmailField()
    when_added = models.DateTimeField()
    # @@@ who added?
    # @@@ comment field?
    
    objects = DontSendEntryManager()
    
    class Meta:
        verbose_name = "don't send entry"
        verbose_name_plural = "don't send entries"


RESULT_CODES = (
    ("1", "success"),
    ("2", "don't send"),
    ("3", "failure"),
    # @@@ other types of failure?
)


class MessageLogManager(models.Manager):
    
    def log(self, message, result_code, log_message=""):
        """
        create a log entry for an attempt to send the given message and
        record the given result and (optionally) a log message
        """
        
        return self.create(
            message_data = message.message_data,
            when_added = message.when_added,
            priority = message.priority,
            # @@@ other fields from Message
            result = result_code,
            log_message = log_message,
        )


class MessageLog(models.Model):
    
    # fields from Message
    message_data = models.TextField()
    when_added = models.DateTimeField()
    priority = models.CharField(max_length=1, choices=PRIORITIES)
    # @@@ campaign?
    
    # additional logging fields
    when_attempted = models.DateTimeField(default=datetime.now)
    result = models.CharField(max_length=1, choices=RESULT_CODES)
    log_message = models.TextField()
    
    objects = MessageLogManager()
    
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
