=====
Usage
=====

First, add "mailer" to your ``INSTALLED_APPS`` in your settings.py.
Run ``./manage.py migrate`` to install models.

Using EMAIL_BACKEND
===================

This is the preferred and easiest way to use django-mailer.

To automatically switch all your mail to use django-mailer, first set
EMAIL_BACKEND::

    EMAIL_BACKEND = "mailer.backend.DbBackend"

If you were previously using a non-default EMAIL_BACKEND, you need to configure
the MAILER_EMAIL_BACKEND setting, so that django-mailer knows how to actually send
the mail::

    MAILER_EMAIL_BACKEND = "your.actual.EmailBackend"

Now, just use the normal `Django mail functions
<https://docs.djangoproject.com/en/dev/topics/email/>`_ for sending email. These
functions will store mail on a queue in the database, which must be sent as
below.

Explicitly putting mail on the queue
====================================

If you don't want to send all email through django-mailer, you can send mail
using ``mailer.send_mail``, which has the same signature as Django's
``send_mail`` function.

You can also do the following::

    # favour django-mailer but fall back to django.core.mail
    from django.conf import settings

    if "mailer" in settings.INSTALLED_APPS:
        from mailer import send_mail
    else:
        from django.core.mail import send_mail

and then just call send_mail like you normally would in Django::

    send_mail(subject, message_body, settings.DEFAULT_FROM_EMAIL, recipients)

There is also a convenience function ``mailer.send_html_mail`` for creating HTML
(this function is **not** in Django)::

    send_html_mail(subject, message_plaintext, message_html, settings.DEFAULT_FROM_EMAIL, recipients)

Additionally you can send all the admins as specified in the ``ADMIN``
setting by calling::

    mail_admins(subject, message_body)

or all managers as defined in the ``MANAGERS`` setting by calling::

    mail_managers(subject, message_body)

Clear queue with command extensions
===================================

With mailer in your INSTALLED_APPS, there will be three new manage.py commands
you can run:

* ``send_mail`` will clear the current message queue. If there are any
  failures, they will be marked deferred and will not be attempted again by
  ``send_mail``.

* ``retry_deferred`` will move any deferred mail back into the normal queue
  (so it will be attempted again on the next ``send_mail``).

* ``purge_mail_log`` will remove old successful message logs from the database, to prevent it from filling up your database


You may want to set these up via cron to run regularly::


    *       * * * * (/path/to/your/python /path/to/your/manage.py send_mail >> ~/cron_mail.log 2>&1)
    0,20,40 * * * * (/path/to/your/python /path/to/your/manage.py retry_deferred >> ~/cron_mail_deferred.log 2>&1)
    0 0 * * * (/path/to/your/python /path/to/your/manage.py purge_mail_log 7 >> ~/cron_mail_purge.log 2>&1)

For use in Pinax, for example, that might look like::

    * * * * * (cd $PINAX; /usr/local/bin/python2.5 manage.py send_mail >> $PINAX/cron_mail.log 2>&1)
    0,20,40 * * * * (cd $PINAX; /usr/local/bin/python2.5 manage.py retry_deferred >> $PINAX/cron_mail_deferred.log 2>&1)
    0 0 * * * (cd $PINAX; /usr/local/bin/python2.5 manage.py purge_mail_log 7 >> $PINAX/cron_mail_purge.log 2>&1)

This attempts to send mail every minute with a retry on failure every 20 minutes and purging the mail log for entries older than 7 days.

``manage.py send_mail`` uses a lock file in case clearing the queue takes
longer than the interval between calling ``manage.py send_mail``.

Note that if your project lives inside a virtualenv, you also have to execute
this command from the virtualenv. The same, naturally, applies also if you're
executing it with cron. The `Pinax documentation`_ explains that in more
details.

.. _pinax documentation: http://pinaxproject.com/docs/dev/deployment.html#sending-mail-and-notices

===================
Using EMAIL_BACKEND
===================

To automatically switch all your mail to use django-mailer, instead of changing imports
you can also use the EMAIL_BACKEND feature that was introduced in Django 1.2. In
your settings file, you first have to set EMAIL_BACKEND::

    EMAIL_BACKEND = "mailer.backend.DbBackend"

If you were previously using a non-default EMAIL_BACKEND, you need to configure
the MAILER_EMAIL_BACKEND setting, so that django-mailer knows how to actually send
the mail::

    MAILER_EMAIL_BACKEND = "your.actual.EmailBackend"

Controlling the delivery process
================================

If you wish to have a finer control over the delivery process, which defaults
to deliver everything in the queue, you can use the following 3 variables
(default values shown)::

    MAILER_EMAIL_MAX_BATCH = None  # integer or None
    MAILER_EMAIL_MAX_DEFERRED = None  # integer or None
    MAILER_EMAIL_THROTTLE = 0  # passed to time.sleep()

These control how many emails are sent successfully before stopping the
current run `MAILER_EMAIL_MAX_BATCH`, after how many failed/deferred emails
should it stop `MAILER_EMAIL_MAX_DEFERRED` and how much time to wait between
each email `MAILER_EMAIL_THROTTLE`.

Unprocessed emails will be evaluated in the following delivery iterations.


