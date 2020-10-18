Change log
==========

2.1 - under development
-----------------------

* Added ``-r`` option to ``purge_mail_log`` management command. Thanks julienc91
* Fixed deprecation warnings on Django 3.1
* added ability to override the default error handler


2.0.1 - 2020-03-01
------------------

* Fixed issue with migration that some people experienced (see `PR 118
  <https://github.com/pinax/django-mailer/pull/118>`_)

2.0 - 2019-09-23
----------------

* Django 3.0 support
* Dropped support for old Django versions (before 1.11)
* Changed DB ``priority`` field to an integer, instead of text field container an integer
* Multi-process safety for sending emails via database row-level locking.

  Previously, there was a file-system based lock to ensure that multiple
  processes were not attempting to send the mail queue, to stop multiple sending
  of the same email. However, this mechanism only works if all processes that
  might be attempting to do this are on the same machine with access to the same
  file-system.

  Now, in addition to this file lock, we use transactions and row-level locking
  in the database when attempting to send a message, which guarantees that only
  one process can send the message. In addition, for databases that support
  ``NOWAIT`` with ``SELECT FOR UPDATE``, such as PostgreSQL, if multiple
  processes attempt to send the mail queue at the same time, the work should be
  distributed between them (rather than being done by only one process).

  A negative consequence is that **SQLite support is degraded**: due to the way
  it implements locking and our use of transactions when sending the email
  queue, you can get exceptions in other processes that are trying to add items
  to the queue. Use of SQLite with django-mailer is **not recommended**.

* ``retry_deferred`` command has also been updated to be simpler and work
  correctly for multiple processes.

* Dropped some backwards compat support for Django < 1.8. If you are upgrading
  from a version of Django before 1.8, you should install a version of
  django-mailer < 2.0, do ``send_all`` to flush the queue, then upgrade
  django-mailer to 2.0 or later.

1.2.6 - 2019-04-03
------------------

* Official Django 2.1 and 2.2 support.
* Don't close DB connection in management commands.
  This is unnecessary with modern Django.

1.2.5
-----

* Fixed packaging file permission problems.
* Added Japanese locale (thanks msk7777)

1.2.4
-----

* Django 2.0 support.

1.2.3
-----

* Fixed crasher with models ``__str__``

1.2.2
-----

* Django 1.10 support.
* Fixed reprs for Message and MessageLog.

1.2.1
-----

* More helpful admin for Message and MessageLog
* Handle exceptions from really old Django versions

1.2.0
-----

* Save the ``Message-ID`` header on ``Message`` explicitly to enable finding
  emails using this identifier.

  This includes a database schema migration.


1.1.0
-----

* Deprecated calling ``send_mail`` and ``send_html_mail`` using ``priority``
  kwargs ``"high"``, ``"medium"``, and ``"low"``. Instead you should use
  ``PRIORITY_HIGH``, ``PRIORITY_MEDIUM`` and ``PRIORITY_LOW`` from
  ``mailer.models``.

* Fixed bug with migrations for Django 1.7, which wanted to create a migration
  to 'fix' the EmailField length back down to 75 instead of 254.


1.0.1
-----

* Included migrations - for both South and Django 1.7 native migrations.

  Note:

  * If you use South, you will need at least South 1.0
  * You will need to use '--fake' or '--fake-initial' on existing installations.

  These migrations were supposed to be in 1.0.0 but were omitted due to a
  packaging error.

1.0.0
-----

* Throttling of email sending
* Django 1.8 support
* Admin tweaks and improvements
* Various other fixes, especially from Renato Alves <alves.rjc@gmail.com> - thank you!

0.1.0
-----

* First PyPI version
