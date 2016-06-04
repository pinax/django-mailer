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
-----

Pinax is an open-source platform built on the Django Web Framework. It is an ecosystem of reusable Django apps, themes, and starter project templates.
This collection can be found at http://pinaxproject.com.

This app was developed as part of the Pinax ecosystem but is just a Django app and can be used independently of other Pinax apps.


django-mailer
-------------

``django-mailer`` is a reusable Django app for queuing the sending of email.


Getting Started
---------------

Simple usage instructions:

In ``settings.py``:
::

    INSTALLED_APPS = [
        ...
        "mailer",
        ...
    ]

    EMAIL_BACKEND = "mailer.backend.DbBackend"

Run database migrations to set up the needed database tables.

Then send email in the normal way, as per the `Django email docs <https://docs.djangoproject.com/en/stable/topics/email/>`_, and they will be added to the queue.

To actually send the messages on the queue, add this to a cron job file or equivalent::

    *       * * * * (/path/to/your/python /path/to/your/manage.py send_mail >> ~/cron_mail.log 2>&1)
    0,20,40 * * * * (/path/to/your/python /path/to/your/manage.py retry_deferred >> ~/cron_mail_deferred.log 2>&1)

To prevent from the database filling up with the message log, you should clean it up every once in a while.

To remove successful log entries older than a week, add this to a cron job file or equivalent::

    0 0 * * * (/path/to/your/python /path/to/your/manage.py purge_mail_log 7 >> ~/cron_mail_purge.log 2>&1)

Documentation
-------------

See ``usage.rst`` in the docs for more advanced use cases - https://github.com/pinax/django-mailer/blob/master/docs/usage.rst#usage.
The Pinax documentation is available at http://pinaxproject.com/pinax/.


Contribute
----------

See ``CONTRIBUTING.rst`` for information about contributing patches to ``django-mailer``.

See this blog post http://blog.pinaxproject.com/2016/02/26/recap-february-pinax-hangout/ including a video, or our How to Contribute (http://pinaxproject.com/pinax/how_to_contribute/) section for an overview on how contributing to Pinax works. For concrete contribution ideas, please see our Ways to Contribute/What We Need Help With (http://pinaxproject.com/pinax/ways_to_contribute/) section.

In case of any questions we recommend you join our Pinax Slack team (http://slack.pinaxproject.com) and ping us there instead of creating an issue on GitHub. Creating issues on GitHub is of course also valid but we are usually able to help you faster if you ping us in Slack.

We also highly recommend reading our Open Source and Self-Care blog post (http://blog.pinaxproject.com/2016/01/19/open-source-and-self-care/).


Code of Conduct
---------------

In order to foster a kind, inclusive, and harassment-free community, the Pinax Project has a code of conduct, which can be found here  http://pinaxproject.com/pinax/code_of_conduct/.
We ask you to treat everyone as a smart human programmer that shares an interest in Python, Django, and Pinax with you.



Pinax Project Blog and Twitter
------------------------------

For updates and news regarding the Pinax Project, please follow us on Twitter at @pinaxproject and check out our blog http://blog.pinaxproject.com.
