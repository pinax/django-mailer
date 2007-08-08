from datetime import datetime

from django.db import models



PRIORITIES = (
    ('1', 'high'),
    ('2', 'medium'),
    ('3', 'low'),
)



class MessageManager(models.Manager):
    
    def send_order(self):
        """
        the messages in the queue in the order they should be sent
        """
        
        return self.order_by('priority', 'when_added')


class Message(models.Model):
    
    objects = MessageManager()
    
    to_address = models.CharField(maxlength=50)
    from_address = models.CharField(maxlength=50)
    subject = models.CharField(maxlength=100)
    message_body = models.TextField()
    when_added = models.DateTimeField()
    priority = models.CharField(maxlength=1, choices=PRIORITIES)
    # @@@ campaign?
    # @@@ content_type?
    
    class Admin:
        list_display = ('id', 'to_address', 'subject', 'when_added', 'priority')



class DontSendEntryManager(models.Manager):
    
    def has_address(self, address):
        """
        is the given address on the don't send list?
        """
        
        if self.filter(to_address=address).count() > 0: # @@@ is there a better way?
            return True
        else:
            return False


class DontSendEntry(models.Model):
    
    objects = DontSendEntryManager()
    
    to_address = models.CharField(maxlength=50)
    when_added = models.DateTimeField()
    # @@@ who added?
    # @@@ comment field?
    
    class Meta:
        verbose_name = 'don\'t send entry'
        verbose_name_plural = 'don\'t send entries'
    
    class Admin:
        list_display = ('to_address', 'when_added')



RESULT_CODES = (
    ('1', 'success'),
    ('2', 'don\'t send'),
    ('3', 'failure'),
    # @@@ other types of failure?
)



class MessageLogManager(models.Manager):
    
    def log(self, message, result_code, log_message = ''):
        """
        create a log entry for an attempt to send the given message and
        record the given result and (optionally) a log message
        """
        
        message_log = self.create(
            to_address = message.to_address,
            from_address = message.from_address,
            subject = message.subject,
            message_body = message.message_body,
            when_added = message.when_added,
            priority = message.priority,
            # @@@ other fields from Message
            when_attempted = datetime.now(),
            result = result_code,
            log_message = log_message,
        )
        message_log.save()


class MessageLog(models.Model):
    
    objects = MessageLogManager()
    
    # fields from Message
    to_address = models.CharField(maxlength=50)
    from_address = models.CharField(maxlength=50)
    subject = models.CharField(maxlength=100)
    message_body = models.TextField()
    when_added = models.DateTimeField()
    priority = models.CharField(maxlength=1, choices=PRIORITIES)
    # @@@ campaign?
    
    # additional logging fields
    when_attempted = models.DateTimeField()
    result = models.CharField(maxlength=1, choices=RESULT_CODES)
    log_message = models.TextField()
    
    class Admin:
        list_display = ('id', 'to_address', 'subject', 'when_attempted', 'result')
