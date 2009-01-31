Overview
========

This is a complete rewrite of the `Archlinux User Repository
<http://aur.archlinux.org>`_ in Python/Django. It was created to improve the
usability and usefulness of the AUR, and to make it more maintainable.

The purpose of this application is to provide a catalogue of Archlinux
PKGBUILDs and binary packages. It allows user-contributed PKGBUILDs
without any verification process, beyond that which can be performed
automatically.

For more information about the development process see the `AUR 2 article on
the Archlinux wiki <http://wiki.archlinux.org/index.php/AUR_2>`_

Dependencies
============

* `Django <http://www.djangoproject.com>`_ >= 1.0

If you use ``pip``, a ``pip-requirements.txt`` file is provided. It can be used as
such::

    pip install -r pip-requirements.txt


Configuration
=============

After all dependencies have been installed the ``settings.py`` file should be
configured, a prototype has been provided as ``settings.py.proto``. For
development purposes, the most important settings are related to the database.
Typically ``sqlite3`` would be used, e.g.::

    DATABASE_ENGINE = 'sqlite3'
    DATABASE_NAME = 'database.sqlite3'
    # These variables can be left blank
    DATABASE_USER = ''
    DATABASE_PASSWORD = ''
    DATABASE_HOST = ''
    DATABASE_PORT = ''

The *DEPLOY_PATH* should be set. For development purposes this can be the
project directory::

    import os
    DEPLOY_PATH = os.path.dirname(__file__)

Finally the last required variables are *MEDIA_ROOT*, *MEDIA_URL* and
*ADMIN_MEDIA_PREFIX*. *MEDIA_ROOT* can also take advantage of *DEPLOY_PATH*::

    MEDIA_ROOT = os.path.join(DEPLOY_PATH, 'media')

The *MEDIA_URL* should point to ``/media/``. Using the Django dev server, this would be::

    MEDIA_URL = 'http://localhost:8000/media/'

The *ADMIN_MEDIA_PREFIX* is only required if the admin app is used. It can be
left as is, but MEDIA_URL would have to to be changed. The suggested
configuration is to set it to ``/media/admin/`` and symlink that directory to the
admin media directory (``django/contrib/admin/media``) in your Django
installation.
