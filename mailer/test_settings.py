
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    },
}

INSTALLED_APPS = [
    # 'django.contrib.auth',
    # 'django.contrib.admin',
    # 'django.contrib.sessions',
    # 'django.contrib.sites',
    # 'django.contrib.contenttypes',
    'mailer',
]

# TEMPLATE_CONTEXT_PROCESSORS = [
#     "django.contrib.auth.context_processors.auth",
#     "django.core.context_processors.debug",
#     "django.core.context_processors.i18n",
#     "django.core.context_processors.media",
#     "django.core.context_processors.static",
#     "django.core.context_processors.tz",
#     "django.contrib.messages.context_processors.messages",
#     "django.core.context_processors.request",
# ]

# ROOT_URLCONF = 'django_easyfilters.tests.urls'

# DEBUG = True

# SITE_ID = 1

# STATIC_URL = '/static/'

SECRET_KEY = 'x'
