django-mailer
-------------

.. image:: http://slack.pinaxproject.com/badge.svg
   :target: http://slack.pinaxproject.com/

.. image:: https://img.shields.io/travis/pinax/django-mailer.svg
    :target: https://travis-ci.org/pinax/django-mailer

.. image:: https://img.shields.io/coveralls/pinax/django-mailer.svg
    :target: https://coveralls.io/r/pinax/django-mailer

.. image:: https://img.shields.io/pypi/dm/django-mailer.svg
    :target:  https://pypi.python.org/pypi/django-mailer/

.. image:: https://img.shields.io/pypi/v/django-mailer.svg
    :target:  https://pypi.python.org/pypi/django-mailer/

.. image:: https://img.shields.io/badge/license-MIT-blue.svg
    :target:  https://pypi.python.org/pypi/django-mailer/



django-mailer by James Tauber <http://jtauber.com/>
https://github.com/pinax/django-mailer

A reusable Django app for queuing the sending of email

Simple usage instructions:

In ``settings.py``:
::

    INSTALLED_APPS = [
        ...
        "mailer",
        ...
   ]

    EMAIL_BACKEND = "mailer.backend.DbBackend"

In a cron job file:
::

    *       * * * * (/path/to/your/python /path/to/your/manage.py send_mail >> ~/cron_mail.log 2>&1)
    0,20,40 * * * * (/path/to/your/python /path/to/your/manage.py retry_deferred >> ~/cron_mail_deferred.log 2>&1)

See ``usage.rst`` in the docs for more advanced use cases - https://github.com/pinax/django-mailer/blob/master/docs/usage.rst#usage

See CONTRIBUTING.rst for information about contributing patches to django-mailer.
