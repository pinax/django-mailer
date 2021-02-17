#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name="django-mailer",
    version="2.1",
    description="A reusable Django app for queuing the sending of email",
    long_description="""``django-mailer`` is a reusable Django app for queuing the sending of email.
It works by storing email in the database for later sending.
The main reason for doing this is that for many apps, the database will be
much more reliable and faster than other email sending backends which require
3rd party services e.g. SMTP or an HTTP API. By storing and sending later, we can
return succeed immediately, and then attempt actual email sending in the background,
with retries if needed.""",
    author="Pinax Team",
    author_email="developers@pinaxproject.com",
    url="http://github.com/pinax/django-mailer/",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    package_data={'mailer': ['locale/*/LC_MESSAGES/*.*']},
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Framework :: Django",
    ],
    install_requires=[
        'Django >= 1.11',
        'lockfile >= 0.8',
        'six',
        ],
)
