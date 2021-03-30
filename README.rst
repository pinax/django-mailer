Django Mailer
-------------

``django-mailer`` is a reusable Django app for queuing the sending of email. 
It works by storing email in the database for later sending. This is a fork of 
`django-mailer by Pinax <https://github.com/pinax/django-mailer/>`_ adding some new features,
such as asynchronously email sending, multi account support, and celery tasks instead of cron jobs.

Keep in mind that file attachments are also temporarily stored in the database, which 
means if you are sending files larger than several hundred KB in size, you are likely 
to run into database limitations on how large your query can be. If this happens, 
you'll either need to fall back to using Django's default mail backend, or increase 
your database limits (a procedure that depends on which database you are using).


Requirements
------------

* Django >= 1.11
* celery >= 4.2

* Databases: django-mailer supports all databases that Django supports, with the following notes:

  * SQLite: you may experience 'database is locked' errors if the ``send_mail``
    command runs when anything else is attempting to put items on the queue. For this reason
    SQLite is not recommended for use with django-mailer.


Instalation
-----------
::

    pip install git+git://github.com/danielslz/django-mailer


Getting Started
---------------

Simple usage instructions:

You need to set at least the variables above. 

In ``settings.py``:
::
    
    INSTALLED_APPS += (
        'mailer',
    )

    EMAIL_BACKEND = 'mailer.backend.DbBackend'
    
    MAILER_NUM_ACCOUNTS = 2
    MAILER_EMAIL_ACCOUNT_LIST = [
        {
            'EMAIL_HOST_1': 'smtp.mailserver.com',
            'EMAIL_PORT_1': 587,
            'EMAIL_HOST_USER_1': 'user_1@mailserver.com',
            'EMAIL_HOST_PASSWORD_1': '..super_password_1..',
            'EMAIL_USE_TLS_1': True,
        },
        {
            'EMAIL_HOST_2': 'smtp.mailserver.com',
            'EMAIL_PORT_2': 587,
            'EMAIL_HOST_USER_2': 'user_2@mailserver.com',
            'EMAIL_HOST_PASSWORD_2': '..super_password_2..',
            'EMAIL_USE_TLS_2': True,
        }
    ]
    MAILER_DAILY_SENDING_LIMIT_PER_ACCOUNT = 1000
    MAILER_SENDING_LIMIT_PER_RUN = 100


Run database migrations to set up the needed database tables.

Then send email in the normal way, as per the `Django email docs <https://docs.djangoproject.com/en/stable/topics/email/>`_, and they will be added to the queue.

To actually send the messages on the queue, add this to a cron job file or equivalent::

    *       * * * * (/path/to/your/python /path/to/your/manage.py send_mail >> ~/cron_mail.log 2>&1)
    0,20,40 * * * * (/path/to/your/python /path/to/your/manage.py retry_deferred >> ~/cron_mail_deferred.log 2>&1)

To prevent from the database filling up with the message log, you should clean it up every once in a while.

To remove log entries older than a week, add this to a cron job file or equivalent::

    0 0 * * * (/path/to/your/python /path/to/your/manage.py purge_mail_log 7 >> ~/cron_mail_purge.log 2>&1)

Or, if your project use celery, run a worker with beat scheduler::
    
    /path/to/your/celery -A your_app worker -B -l info


Advanced usage
--------------

If you want more control over how this lib is executed, you can use the settings above:

* MAILER_ASYNC_SEND
    * Default: False
    * If True, emails are sent asynchronously
* MAILER_MINUTS_TO_SEND_MAIL
    * Default: 5
    * Time in minutos to wake up the celery task to send mail
* MAILER_MINUTS_TO_RETRY_DEFERRED
    * Default: 30
    * Time in minutos to wake up the celery task to retry deferred mail
* MAILER_DAYS_PURGE_MAIL_LOG
    * Default: 7
    * Number of days to delete old sended emails in log
* MAILER_EMAIL_THROTTLE
    * Default: 0
    * When delivering, wait some time between emails to avoid server overload
* MAILER_SUBJECTS_HIGH_PRIORITY
    * Default: ''
    * List of comma separated words to put mail in high priority list
* MAILER_SUBJECTS_LOW_PRIORITY
    * Default: ''
    * List of comma separated words to put mail in low priority list
* MAILER_LOCK_PATH
    * Default: ''
    * If set, the path to put the lock_file when delivering emails

