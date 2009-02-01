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
* `django-registration <http://bitbucket.org/ubernostrum/django-registration>`_
* `django-tagging <http://code.google.com/p/django-tagging>`_

If you use ``pip``, a ``pip-requirements.txt`` file is provided. It can be used as
such::

    pip install -r pip-requirements.txt


Configuration
=============

After all dependencies have been installed the ``settings_local.py``
file should be configured, a prototype has been provided as
``settings_local.py.sample``. The default ``settings.py`` file has
defaults targeted for a development environment. On a production system
at least the settings in ``settings_local.py.sample`` should configured.

The *ADMIN_MEDIA_PREFIX* is only required if the admin app is used. It can be
left as is, but MEDIA_URL would have to to be changed. The suggested
configuration is to set it to ``/media/admin/`` and symlink that directory to the
admin media directory (``django/contrib/admin/media``) in your Django
installation.

A functioning email server is necessary for various parts of the application.
The *EMAIL_HOST* and *EMAIL_PORT* settings should be configured appropriately.
For development purposes, a dummy server can be used instead::

    python -m smtpd -n -c DebuggingServer localhost:1025

At this point it would be a good idea to run all tests, to make sure everything works::

    python manage.py test
