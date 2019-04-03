Change log
==========

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
