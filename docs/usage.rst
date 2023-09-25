=====
Usage
=====

First, add "mailer" to your ``INSTALLED_APPS`` in your ``settings.py``:

In ``settings.py``:

.. code-block:: python

    INSTALLED_APPS = [
        ...
        "mailer",
        ...
    ]


Run ``./manage.py migrate`` to install models.


Putting mail on the queue
=========================

Using EMAIL_BACKEND
-------------------

This is the preferred and easiest way to use django-mailer.

To automatically switch all your mail to use django-mailer, set
``EMAIL_BACKEND``:

.. code-block:: python

    EMAIL_BACKEND = "mailer.backend.DbBackend"

If you were previously using a non-default ``EMAIL_BACKEND``, you need to configure
the ``MAILER_EMAIL_BACKEND`` setting, so that django-mailer knows how to actually send
the mail:

.. code-block:: python

    MAILER_EMAIL_BACKEND = "your.actual.EmailBackend"

For testing purposes, you could set this to
``"django.core.mail.backends.console.EmailBackend"`` to just print emails to the
console.

Now, just use the normal `Django mail functions
<https://docs.djangoproject.com/en/stable/topics/email/>`_ for sending email. These
functions will store mail on a queue in the database, which must be sent as
below.

Alternative: explicitly putting mail on the queue
-------------------------------------------------

As an alternative to the above, which dates from before there was such as thing
as an "email backend" in Django, you can import the ``send_mail`` function (and
similar) from ``mailer`` instead of from ``django.core.mail``. There is also a
``send_html_mail`` convenience function. However, we no longer guarantee that
these functions will have a 100% compatible signature with the Django version,
so we recommend you don't use these functions.

Sending mail
============

Having put mail on the queue, you need to arrange for the mail to be sent, which
can be done using the management commands that ``django-mailer`` adds.

``send_mail``
-------------

This is a management command that can be run as a scheduled task. It triggers
the ``send_all()`` command, which sends all the mail on the queue.

If there are any failures, they will be marked deferred and will not be
attempted again by ``send_all()``.


``runmailer``
-------------

This is an alternative to ``send_mail``, which keeps running and checks the
database for new messages every ``MAILER_EMPTY_QUEUE_SLEEP`` (default: 30)
seconds. It should be used *instead* of ``send_mail`` to circumvent the maximum
frequency of once per minute inherent to cron.


``runmailer_pg``
----------------

This is a more advanced alternative to ``send_mail``, for PostgreSQL only.

This process keeps running and checks the database for new messages every
``MAILER_EMPTY_QUEUE_SLEEP`` (default: 30) seconds. In addition, it uses
PostgreSQL’s NOTIFY/LISTEN pub-sub mechanism to send emails as soon
as they have been added to the database (and the transaction is committed).

Under the hood the command automatically adds a trigger to the ``Message`` table
which sends a NOTIFY and then LISTENs on the same channel, using a single worker
thread to send emails. It uses the same ``send_all()`` command internally as
other mechanisms.

To add rate controls, the ``MAILER_EMAIL_MAX_BATCH`` setting mentioned below is
not very effective. While it is still honoured, a “batch” is now triggered
whenever new mail is put on the queue, rather than only after a scheduled delay.
This means you will need to use ``MAILER_EMAIL_THROTTLE`` (see below) to limit
the number of emails sent.


``retry_deferred``
------------------

This will move any deferred mail back into the normal queue, so it will be
attempted again on the next ``send_mail``. It should be run at regular period to
attempt to fix failures caused by network outages or other temporary problems.

``purge_mail_log``
------------------

This will remove old successful message logs from the database, to prevent it
from filling up your database. Use the ``-r failure`` option to remove only
failed message logs instead, or ``-r all`` to remove them all.


Example cron
============

An example cron file looks like this::

    *       * * * * (/path/to/your/python /path/to/your/manage.py send_mail >> ~/cron_mail.log 2>&1)
    0,20,40 * * * * (/path/to/your/python /path/to/your/manage.py retry_deferred >> ~/cron_mail_deferred.log 2>&1)
    0 0 * * * (/path/to/your/python /path/to/your/manage.py purge_mail_log 7 >> ~/cron_mail_purge.log 2>&1)

For use in Pinax, for example, that might look like::

    * * * * * (cd $PINAX; /usr/local/bin/python manage.py send_mail >> $PINAX/cron_mail.log 2>&1)
    0,20,40 * * * * (cd $PINAX; /usr/local/bin/python manage.py retry_deferred >> $PINAX/cron_mail_deferred.log 2>&1)
    0 0 * * * (cd $PINAX; /usr/local/bin/python manage.py purge_mail_log 7 >> $PINAX/cron_mail_purge.log 2>&1)

This attempts to send mail every minute with a retry on failure every 20
minutes, and purges the mail log for entries older than 7 days.

If you are using ``runmailer`` or ``runmailer_pg`` you don’t need the
``send_mail`` item.


Running ``runmailer`` and ``runmailer_pg``
==========================================

If you are using ``runmailer`` or ``runmailer_pg`` instead of ``send_mail``,
it's up to you to keep this command running in the background, restarting it if
it crashes. This can be achieved using `supervisord`_ or similar software, such
as a systemd service unit file.

.. _pinax documentation: http://pinaxproject.com/docs/dev/deployment.html#sending-mail-and-notices
.. _supervisord: http://supervisord.org/

Locking
=======

The ``send_all`` command uses a filesystem-based lock file in case clearing the
queue takes longer than the interval between calling ``send_all()``. This works
to stop multiple workers on a single machine from processing the messages
multiple times.

To stop workers processes on different machines from sending the same mail
multiple times, it also uses database-level locking where possible. Where
available this is more reliable than filesystem-based locks.

If you need to be able to control where django-mailer puts its lock file, you
can set ``MAILER_LOCK_PATH`` to a full absolute path to the file to be used as a
lock. The extension ".lock" will be added. The process running ``send_all()``
needs to have permissions to create and delete this file, and others in the same
directory. With the default value of ``None`` django-mailer will use a path in
current working directory.

If you want to disable the file-based locking, you can set the
``MAILER_USE_FILE_LOCK`` setting to ``False``.


Controlling the delivery process
================================

If you wish to have a finer control over the delivery process, which defaults
to deliver everything in the queue, you can use the following 3 settings:

* ``MAILER_EMAIL_MAX_BATCH``: integer or ``None``, defaults to ``None`` - how
  many emails are sent successfully before stopping the current run of ``send_all()``

* ``MAILER_EMAIL_MAX_DEFERRED``: integer or ``None``, defaults to ``None`` -
  after how many failed/deferred emails ``send_all()`` should stop.

* ``MAILER_EMAIL_THROTTLE``: integer, defaults to 0 - how many seconds to sleep
  after sending an email.

If limited by ``MAILER_EMAIL_MAX_BATCH`` or ``MAILER_EMAIL_MAX_DEFERRED``,
unprocessed emails will be evaluated in the following delivery iterations.

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

Any other exception is re-raised. This is done for backwards-compatibility as
well as for flexibility: we would otherwise have to maintain an extensive and
changing list of exception types, which does not scale, and you get the chance
to do error handling that fits your needs.

When the default behavior does not fit your needs, you can specify your
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
            # trying to re-send this very message desperately
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
