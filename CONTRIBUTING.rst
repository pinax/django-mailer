How to Contribute
=================

There are many ways you can help contribute to django-mailer and the
various apps, themes, and starter projects that it is made up of. Contributing
code, writing documentation, reporting bugs, as well as reading and providing
feedback on issues and pull requests, all are valid and necessary ways to
help.

Local development setup
-----------------------

To set up your environment to be able to work on django-mailer, do the following:

1. Fork the django-mailer repo on GitHub.

2. Clone your fork locally::

     $ git clone git@github.com:your_name_here/django-mailer.git
     $ cd django-mailer/

3. Install your local copy into a virtualenv. Assuming you have virtualenvwrapper::

    $ mkvirtualenv django-mailer
    $ python setup.py develop

4. Install test requirements::

    $ pip install coverage mock

5. Create a branch for local development::

    $ git checkout -b name-of-your-bugfix-or-feature

6. Now you can make your changes locally. Run the tests in the virtualenv using::

    $ ./runtests.py

   To run the tests in all supported environments, do::

    $ pip install tox
    $ tox

7. When your changes are done, push the branch to GitHub, and create a pull
   request.

Coding style
------------

When writing code to be included in django-mailer keep our style in mind:

* Follow `PEP8 <http://www.python.org/dev/peps/pep-0008/>`_ . There are some
  cases where we do not follow PEP8 but it is an excellent starting point.
* Follow `Django's coding style <http://docs.djangoproject.com/en/dev/internals/contributing/#coding-style>`_ 
  we're pretty much in agreement on Django style outlined there.


Pull Requests
-------------

Please keep your pull requests focused on one specific thing only. If you
have a number of contributions to make, then please send separate pull
requests. It is much easier on maintainers to receive small, well defined,
pull requests, than it is to have a single large one that batches up a
lot of unrelated commits.

If you ended up making multiple commits for one logical change, please
rebase into a single commit::

    git rebase -i HEAD~10  # where 10 is the number of commits back you need

This will pop up an editor with your commits and some instructions you want
to squash commits down by replacing 'pick' with 's' to have it combined with
the commit before it. You can squash multiple ones at the same time.

When you save and exit the text editor where you were squashing commits, git
will squash them down and then present you with another editor with commit
messages. Choose the one to apply to the squashed commit (or write a new
one entirely.) Save and exit will complete the rebase. Use a forced push to
your fork::

    git push -f
