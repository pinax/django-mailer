from distutils.core import setup


setup(
    name="django-mailer",
    version=__import__("mailer").__version__,
    description="A reusable Django app for queuing the sending of email",
    long_description=open("docs/usage.txt").read(),
    author="James Tauber",
    author_email="jtauber@jtauber.com",
    url="http://code.google.com/p/django-mailer/",
    packages=[
        "mailer",
        "mailer.management",
        "mailer.management.commands",
    ],
    package_dir={"mailer": "mailer"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Framework :: Django",
    ]
)
