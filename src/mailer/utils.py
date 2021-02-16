# -*- coding: utf-8 -*-
"""
Django, our web development framework of choice provides many useful functions,
send_mail() being one of them which we frequently use.

Though convenient, send_mail() in Django is a synchronous operation – meaning
Django will wait for the mail sending process to finish before continuing other tasks.
This is not usually that big of a deal if the mail server Django is configured to use is
located in the same site (and has low latency), but in cases where the mail server is not
located in the same cloud, this could give the impression that your website is slow,
especially in sites with relatively slow internet connectivity (like Indonesia).

Consider a really common scenario where an application automatically sends an email
verification message to a newly registered user. If configured to use a third party SMTP
server like Gmail, the email sending process takes close to half a second if our app is
located in Jakarta. This means that we are adding close a half a second of latency before
rendering a response to the user, making our app look sluggish (in reality the user
creation process itself takes less than 50ms).

So one of our engineers Gilang wrote a simple wrapper around Django’s send_mail() to
perform the task asynchronously using Python’s threading.

http://ui.co.id/blog/asynchronous-send_mail-in-django
"""
import logging
import threading

from mailer.models import (RESULT_FAILURE, RESULT_SUCCESS, MessageLog)


class EmailThread(threading.Thread):
    def __init__(self, email, message, account):
        self.email = email
        self.message = message
        self.account = account
        threading.Thread.__init__(self)

    def run(self):
        # Variable that stores the exception, if raised by someFunction 
        self.exc = None
        try:
            self.email.send()
            raise Exception('An error ocurred')

            self.email.connection = None
            self.message.email = self.email  # For the sake of MessageLog
            MessageLog.objects.log(self.message, RESULT_SUCCESS, account=self.account)
            
            self.message.delete()
        except BaseException as e: 
            self.exc = e
            self.message.defer()
            logging.info("Message deferred due to failure: %s" % e)
            MessageLog.objects.log(self.message, RESULT_FAILURE, log_message=str(e), account=self.account)
    
    def join(self): 
        threading.Thread.join(self) 
        # Since join() returns in caller thread 
        # we re-raise the caught exception 
        # if any was caught 
        if self.exc: 
            raise self.exc 


def send_async_mail(email, message, account):
    t = EmailThread(email, message, account)
    t.start()
