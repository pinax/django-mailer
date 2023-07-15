=====
Usage
=====

First, add "mailer" to your ``INSTALLED_APPS`` in your ``settings.py``.
Run ``./manage.py migrate`` to install models.

Using EMAIL_BACKEND
===================

This is the preferred and easiest way to use django-mailer.

To automatically switch all your mail to use django-mailer, first set
``EMAIL_BACKEND``::

    EMAIL_BACKEND = "mailer.backend.DbBackend"

If you were previously using a non-default ``EMAIL_BACKEND``, you need to configure
the ``MAILER_EMAIL_BACKEND`` setting, so that django-mailer knows how to actually send
the mail::

    MAILER_EMAIL_BACKEND = "your.actual.EmailBackend"

Now, just use the normal `Django mail functions
<https://docs.djangoproject.com/en/stable/topics/email/>`_ for sending email. These
functions will store mail on a queue in the database, which must be sent as
below.

Explicitly putting mail on the queue
====================================

The best method to explicitly send some messages through the django-mailer queue (and perhaps 
not others), is to use the ``connection`` parameter to the normal ``django.core.mail.send_mail``
function or the ``django.core.mail.EmailMessage`` constructor - see the Django docs as above and
the `django.core.mail.get_connection <https://docs.djangoproject.com/en/stable/topics/email/#obtaining-an-instance-of-an-email-backend>`_
function.

Another method to use the django-mailer queue directly, which dates from before there was such 
as thing as an "email backend" in Django, is to import the ``send_mail`` function (and similar)
from ``mailer`` instead of from ``django.core.mail``. There is also a ``send_html_mail`` convenience
function. However, we no longer guarantee that these functions will have a 100% compatible signature
with the Django version, so we recommend you don't use these functions.

Clear queue with command extensions
===================================

With mailer in your ``INSTALLED_APPS``, there will be four new
``manage.py`` commands you can run:

* ``send_mail`` will clear the current message queue. If there are any
  failures, they will be marked deferred and will not be attempted again by
  ``send_mail``.

* ``runmailer`` similar to ``send_mail``, but will keep running and checking the
  database for new messages each ``MAILER_EMPTY_QUEUE_SLEEP`` (default: 30) seconds.
  Can be used *instead* of ``send_mail`` to circumvent the maximum frequency
  of once per minute inherent to cron.

* ``retry_deferred`` will move any deferred mail back into the normal queue
  (so it will be attempted again on the next ``send_mail``).

* ``purge_mail_log`` will remove old successful message logs from the database, to prevent it from filling up your database.
  Use the ``-r failure`` option to remove only failed message logs instead, or ``-r all`` to remove them all.


You may want to set these up via cron to run regularly::


    *       * * * * (/path/to/your/python /path/to/your/manage.py send_mail >> ~/cron_mail.log 2>&1)
    0,20,40 * * * * (/path/to/your/python /path/to/your/manage.py retry_deferred >> ~/cron_mail_deferred.log 2>&1)
    0 0 * * * (/path/to/your/python /path/to/your/manage.py purge_mail_log 7 >> ~/cron_mail_purge.log 2>&1)

For use in Pinax, for example, that might look like::

    * * * * * (cd $PINAX; /usr/local/bin/python manage.py send_mail >> $PINAX/cron_mail.log 2>&1)
    0,20,40 * * * * (cd $PINAX; /usr/local/bin/python manage.py retry_deferred >> $PINAX/cron_mail_deferred.log 2>&1)
    0 0 * * * (cd $PINAX; /usr/local/bin/python manage.py purge_mail_log 7 >> $PINAX/cron_mail_purge.log 2>&1)

This attempts to send mail every minute with a retry on failure every 20
minutes, and purges the mail log for entries older than 7 days.

``manage.py send_mail`` uses a lock file in case clearing the queue takes
longer than the interval between calling ``manage.py send_mail``.

Note that if your project lives inside a virtualenv, you also have to execute
this command from the virtualenv. The same, naturally, applies also if you're
executing it with cron. The `Pinax documentation`_ explains that in more
details.

If you intend to use ``manage.py runmailer`` instead of ``send_mail`` it's
up to you to keep this command running in the background. This can be achieved
using `supervisord`_ or similar software.

.. _pinax documentation: http://pinaxproject.com/docs/dev/deployment.html#sending-mail-and-notices
.. _supervisord: http://supervisord.org/

Controlling the delivery process
================================

If you wish to have a finer control over the delivery process, which defaults
to deliver everything in the queue, you can use the following 3 variables
(default values shown)::

    MAILER_EMAIL_MAX_BATCH = None  # integer or None
    MAILER_EMAIL_MAX_DEFERRED = None  # integer or None
    MAILER_EMAIL_THROTTLE = 0  # passed to time.sleep()

These control how many emails are sent successfully before stopping the
current run ``MAILER_EMAIL_MAX_BATCH``, after how many failed/deferred emails
should it stop ``MAILER_EMAIL_MAX_DEFERRED`` and how much time to wait between
each email ``MAILER_EMAIL_THROTTLE``.

Unprocessed emails will be evaluated in the following delivery iterations.

Error handling
==============

django-mailer comes with a default error handler
``mailer.engine.handle_delivery_exception``.

It marks the related message as deferred for any of these exceptions:

- ``smtplib.SMTPAuthenticationError``
- ``smtplib.SMTPDataError``
- ``smtplib.SMTPRecipientsRefused``
- ``smtplib.SMTPSenderRefused``
- ``socket.error``

Any other exceptions is re-raised.
That is done for backwards-compatibility as well as for flexibility:
we would otherwise have to maintain an extensive and changing
list of exception types, which does not scale, and you get
the chance to do error handling that fits your environment like a glove.

When the default behavior does not fit your environment, you can specify your
own custom delivery error handler through setting ``MAILER_ERROR_HANDLER``.
The value should be a string for use with Django's ``import_string``,
the default is ``"mailer.engine.handle_delivery_exception"``.

Your handler is passed three arguments, in order:

- ``connection`` — the backend connection instance that failed delivery
- ``message`` — the ``Message`` instance that failed delivery
- ``exc`` — the exception instance raised by the mailer backend

Your handler should return a 2-tuple of:

1. a connection instance (or ``None`` to cause a new connection to be created)
2. a string denoting the action taken by the handler,
   either ``"sent"`` or ``"deferred"`` precisely

For an example of a custom error handler::

    def my_handler(connection, message, exc):
        if isinstance(exc, SomeDeliveryException):
            # trying to re-send this very message desparately
            # (if you have good reason to)
            [..]
            status = 'sent'
        elif isinstance(exc, SomeOtherException):
            message.defer()
            connection = None  # i.e. ask for a new connection
            status = 'deferred'
        else:
            raise exc

        return connection, status

Other settings
==============

If you need to be able to control where django-mailer puts its lock file (used
to ensure mail is not sent twice), you can set ``MAILER_LOCK_PATH`` to a full
absolute path to the file to be used as a lock. The extension ".lock" will be
added. The process running ``send_mail`` needs to have permissions to create and
delete this file, and others in the same directory. With the default value of
``None`` django-mailer will use a path in current working directory.

If you need to disable the file-based locking, you can set the
``MAILER_USE_FILE_LOCK`` setting to ``False``.

If you need to change the batch size used by django-mailer to save messages in
``mailer.backend.DbBackend``, you can set ``MAILER_MESSAGES_BATCH_SIZE`` to a
value more suitable for you. This value, which defaults to ``None``, will be passed to
`Django's bulk_create method <https://docs.djangoproject.com/en/stable/ref/models/querysets/#bulk-create>`_
as the ``batch_size`` parameter.

To limit the amount of times a deferred message is retried, you can set
``MAILER_EMAIL_MAX_RETRIES`` to an integer value. The default is ``None``, which means
that the message will be retried indefinitely. If you set this to a value of ``0``,
the message will not be retried at all, any number greater than ``0`` will be the
maximum number of retries (excluding the initial attempt).

Using the DontSendEntry table
=============================

django-mailer creates a ``DontSendEntry`` model, which is used to filter out
recipients from messages being created.

However, note that it's actually only used when directly sending messages through
``mailer.send_mail``, not when mailer is used as an alternate ``EMAIL_BACKEND`` for Django.
Also, even if recipients become empty due to this filtering, the email will be
queued for sending anyway. (A patch to fix these issues would be accepted)
