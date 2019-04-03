Release process
---------------

* Check that the master branching is passing all tests - https://travis-ci.org/pinax/django-mailer

* Ensure correct file permissions::

    $ git ls-tree --full-tree --name-only -r HEAD | xargs chmod ugo+r
    $ find . -type d | xargs chmod ugo+x

  Commit as necessary.

* In CHANGES.rst, change the 'Unreleased' heading to the new version, and commit.

* Change the version in mailer/__init__.py, changing "alpha" to "final" if
  necessary.

* Release::

    $ umask 000
    $ ./setup.py sdist bdist_wheel
    $ twine upload dist/django_mailer-$VERSION-py2.py3-none-any.whl dist/django-mailer-$VERSION.tar.gz

* Tag the release e.g.::

    $ git tag 1.2.0
    $ git push upstream master --tags

Post release
------------

* Add new section 'Unreleased' section at top of CHANGES.rst

* Bump version in mailer/__init__.py (to what it is most likely to be next),
  and change "final" to "alpha".
