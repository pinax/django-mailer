#!/usr/bin/env python
"""
manage.py script used by django-mailer developers to create
DB migrations or test management commands.
"""
import os
from copy import deepcopy

DEFAULT_SETTINGS = dict(
    INSTALLED_APPS=[
        "django.contrib.auth",
        "django.contrib.contenttypes",
        "django.contrib.sites",
        "mailer",
    ],
    DATABASES={
        "default": (
            {
                "ENGINE": "django.db.backends.postgresql_psycopg2",
                "NAME": "mailer",
                "USER": "mailer",
                "PASSWORD": "mailer",
                "PORT": 5432,
                "HOST": "localhost",
                "CONN_MAX_AGE": 30,
            }
            if "MAILER_USE_POSTGRES" in os.environ
            else {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": "test",
            }
        )
    },
    SITE_ID=1,
    SECRET_KEY="notasecret",
    MAILER_EMPTY_QUEUE_SLEEP=10,
    # MAILER_EMAIL_THROTTLE=10,
    EMAIL_BACKEND="mailer.backend.DbBackend",
    MAILER_EMAIL_BACKEND="django.core.mail.backends.console.EmailBackend",
)

if __name__ == "__main__":
    from django.conf import settings
    from django.core import management
    from django.utils.log import DEFAULT_LOGGING

    LOGGING = deepcopy(DEFAULT_LOGGING)

    # For testing runmailer_pg:
    LOGGING["handlers"]["mailer.runmail"] = {
        "level": "INFO",
        "class": "logging.StreamHandler",
        "formatter": "django.server",
    }
    LOGGING["loggers"]["mailer.postgres"] = {
        "handlers": ["mailer.runmail"],
        "level": "INFO",
    }
    LOGGING["loggers"]["mailer.engine"] = {
        "handlers": ["mailer.runmail"],
        "level": "INFO",
    }
    DEFAULT_SETTINGS["LOGGING"] = LOGGING

    settings.configure(**DEFAULT_SETTINGS)
    management.execute_from_command_line()
