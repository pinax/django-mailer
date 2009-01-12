from distutils.core import setup

setup(
    name='django-mailer',
    version=__import__('mailer').__version__,
    description='Mail queuing and management for the Django web framework.',
    long_description=open('docs/usage.txt').read(),
    author='James Tauber',
    author_email='jtauber@jtauber.com',
    url='http://code.google.com/p/django-mailer/',
    packages=[
        'notification',
        'notification.management',
        'notification.management.commands',
    ],
    package_dir={'mailer': 'mailer'},
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Framework :: Django',
    ]
)
