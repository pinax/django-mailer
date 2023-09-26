Django Mailer
-------------

.. image:: https://github.com/pinax/django-mailer/actions/workflows/build.yml/badge.svg
   :target: https://github.com/pinax/django-mailer/actions/workflows/build.yml

.. image:: https://img.shields.io/coveralls/pinax/django-mailer.svg
    :target: https://coveralls.io/r/pinax/django-mailer

.. image:: https://img.shields.io/pypi/dm/django-mailer.svg
    :target:  https://pypi.python.org/pypi/django-mailer/

.. image:: https://img.shields.io/pypi/v/django-mailer.svg
    :target:  https://pypi.python.org/pypi/django-mailer/

.. image:: https://img.shields.io/badge/license-MIT-blue.svg
    :target:  https://pypi.python.org/pypi/django-mailer/


django-mailer
-------------

``django-mailer`` is a reusable Django app for queuing the sending of email. It
works by storing email in the database for later sending. This has a number of
advantages:

- **robustness** - if your email provider goes down or has a temporary error,
  the email won’t be lost. In addition, since the ``send_mail()`` call always
  succeeds (unless your database is out of action), then the HTTP request that
  triggered the email to be sent won’t crash, and any ongoing transaction won’t
  be rolled back.

- **correctness** - when an outgoing email is created as part of a transaction,
  since it is stored in the database it will participate in transactions. This
  means it won’t be sent until the transaction is committed, and won’t be sent
  at all if the transaction is rolled back.


In addition, if you want to ensure that mails are sent very quickly, and without
heaving polling, django-mailer comes with a PostgreSQL specific ``runmailer_pg``
command. This uses PostgreSQL’s `NOTIFY
<https://www.postgresql.org/docs/16/sql-notify.html>`_/`LISTEN
<https://www.postgresql.org/docs/16/sql-listen.html>`_ feature to be able to
send emails as soon as they are added to the queue.


Limitations
-----------

File attachments are also temporarily stored in the database, which means if you
are sending files larger than several hundred KB in size, you are likely to run
into database limitations on how large your query can be. If this happens,
you'll either need to fall back to using Django's default mail backend, or
increase your database limits (a procedure that depends on which database you
are using).

With django-mailer, you can’t know in a Django view function whether the email
has actually been sent or not - the ``send_mail`` function just stores mail on
the queue to be sent later.

django-mailer was developed as part of the `Pinax ecosystem
<http://pinaxproject.com>`_ but is just a Django app and can be used
independently of other Pinax apps.


Requirements
------------

* Django >= 2.2

* Databases: django-mailer supports all databases that Django supports, with the following notes:

  * SQLite: you may experience 'database is locked' errors if the ``send_mail``
    command runs when anything else is attempting to put items on the queue. For this reason
    SQLite is not recommended for use with django-mailer.

  * MySQL: the developers don’t test against MySQL.


Usage
-----

See `usage.rst
<https://github.com/pinax/django-mailer/blob/master/docs/usage.rst#usage>`_ in
the docs.


Support
-------

The Pinax documentation is available at http://pinaxproject.com/pinax/.

This is an Open Source project maintained by volunteers, and outside this
documentation the maintainers do not offer other support. For cases where you
have found a bug you can file a GitHub issue. In case of any questions we
recommend you join the `Pinax Slack team <http://slack.pinaxproject.com>`_ and
ping the Pinax team there instead of creating an issue on GitHub. You may also
be able to get help on other programming sites like `Stack Overflow
<https://stackoverflow.com/>`_.


Contribute
----------

See `CONTRIBUTING.rst <https://github.com/pinax/django-mailer/blob/master/CONTRIBUTING.rst>`_ for information about contributing patches to ``django-mailer``.

See this `blog post including a video <http://blog.pinaxproject.com/2016/02/26/recap-february-pinax-hangout/>`_, or our `How to Contribute <http://pinaxproject.com/pinax/how_to_contribute/>`_ section for an overview on how contributing to Pinax works. For concrete contribution ideas, please see our `Ways to Contribute/What We Need Help With <http://pinaxproject.com/pinax/ways_to_contribute/>`_ section.


We also highly recommend reading our `Open Source and Self-Care blog post <http://blog.pinaxproject.com/2016/01/19/open-source-and-self-care/>`_.


Code of Conduct
---------------

In order to foster a kind, inclusive, and harassment-free community, the Pinax Project has a `code of conduct <http://pinaxproject.com/pinax/code_of_conduct/>`_.
We ask you to treat everyone as a smart human programmer that shares an interest in Python, Django, and Pinax with you.



Pinax Project Blog and Twitter
------------------------------

For updates and news regarding the Pinax Project, please follow us on Twitter at @pinaxproject and check out `our blog <http://blog.pinaxproject.com>`_.
