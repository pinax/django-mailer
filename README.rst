Django Mailer
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
    
    
Pinax
--------

Pinax is an open-source platform built on the Django Web Framework. It is an ecosystem of reusable Django apps, themes, and starter project templates. 
This collection can be found at http://pinaxproject.com.

This app was developed as part of the Pinax ecosystem but is just a Django app and can be used independently of other Pinax apps.


django-mailer
--------------

``django-mailer`` is a reusable Django app for queuing the sending of email.


Getting Started
----------------

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
   

Documentation
---------------

See ``usage.rst`` in the docs for more advanced use cases - https://github.com/pinax/django-mailer/blob/master/docs/usage.rst#usage.
The Pinax documentation is available at http://pinaxproject.com/pinax/.


Contributing
--------------

See CONTRIBUTING.rst for information about contributing patches to django-mailer.


Code of Conduct
-----------------

In order to foster a kind, inclusive, and harassment-free community, the Pinax Project has a code of conduct, which can be found here  http://pinaxproject.com/pinax/code_of_conduct/.


Pinax Project Blog and Twitter
-------------------------------

For updates and news regarding the Pinax Project, please follow us on Twitter at @pinaxproject and check out our blog http://blog.pinaxproject.com.






