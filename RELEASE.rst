Release process
---------------

* Check that the master branching is passing all tests - https://travis-ci.org/pinax/django-mailer

* In CHANGES.rst, change the 'Unreleased' heading to the new version, and commit.

* Change the version in mailer/__init__.py, changing "alpha" to "final" if
  necessary.

* Release::

    $ ./setup.py sdist bdist_wheel register upload

* Tag the release e.g.::

    $ git tag 1.2.0
    $ git push upstream master --tags

Post release
------------

* Add new section 'Unreleased' section at top of CHANGES.rst

* Bump version in mailer/__init__.py (to what it is most likely to be next),
  and change "final" to "alpha".
