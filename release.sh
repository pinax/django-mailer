#!/bin/sh

umask 000
rm -rf build dist
git ls-tree --full-tree --name-only -r HEAD | xargs chmod ugo+r
find src docs tests -type d | xargs chmod ugo+rx

python setup.py sdist bdist_wheel || exit 1

VERSION=$(python setup.py --version) || exit 1
twine upload dist/django_mailer-$VERSION-py3-none-any.whl dist/django-mailer-$VERSION.tar.gz || exit 1

