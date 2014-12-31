#!/usr/bin/env python
DEFAULT_SETTINGS = dict(
    INSTALLED_APPS=[
        "django.contrib.auth",
        "django.contrib.contenttypes",
        "django.contrib.sites",
        "mailer",
    ],
    DATABASES={
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    },
    SITE_ID=1,
    SECRET_KEY="notasecret",
)

if __name__ == "__main__":
    from django.conf import settings
    from django.core import management
    settings.configure(**DEFAULT_SETTINGS)
    management.execute_from_command_line()
