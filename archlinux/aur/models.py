from django.db import models
from django.db import transaction
from django.db import IntegrityError
from django.contrib.auth.models import User
from django.core.mail import send_mass_mail
from django.db.models import signals, permalink
from django.dispatch import dispatcher
from django.template.loader import render_to_string
from django.utils.encoding import smart_unicode

from tagging.fields import TagField

from datetime import datetime
import os

def _get_package_upload_to(instance, filename):
    """Returns a string, replacing the name placeholder with a packages name

    *instance* should be a :class:`PackageFile` or :class:`Package` instance.

    *filename* should be a a string with a named placeholder where the name
    should be inserted, e.g. ``'%(name)s/sources/PKGBUILD'``.

    .. note::

        This is meant for use by :class:`PackageFile` and :class:`Package` as
        the *upload_to* callable
    """
    if hasattr(instance, 'package'):
        package = instance.package
    else:
        package = instance
    return os.path.join('packages', filename % {'name': package.name})


class Architecture(models.Model):
    name = models.CharField(max_length=10)

    def __unicode__(self):
        return self.name


class Repository(models.Model):
    name = models.CharField(max_length=20)

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name_plural = 'repositories'


class License(models.Model):
    name = models.CharField(max_length=24)

    def __unicode__(self):
        return self.name


class Group(models.Model):
    name = models.CharField(max_length=10)

    def __unicode__(self):
        return self.name


class Provision(models.Model):
    name = models.CharField(max_length=30)

    def __unicode__(self):
        return self.name


class Package(models.Model):
    name = models.CharField(unique=True, max_length=30, editable=False)
    version = models.CharField(max_length=20)
    release = models.SmallIntegerField()
    description = models.CharField(max_length=180)
    url = models.CharField(max_length=200, null=True, blank=True)
    maintainers = models.ManyToManyField(User)
    repository = models.ForeignKey(Repository)
    tags = TagField()
    slug = models.SlugField(editable=False)
    tarball = models.FileField(upload_to=_get_package_upload_to)
    licenses = models.ManyToManyField(License, null=True, blank=True)
    architectures = models.ManyToManyField(Architecture)
    depends = models.ManyToManyField('self', null=True, blank=True,
            related_name="reverse_depends", symmetrical=False)
    make_depends = models.ManyToManyField('self', null=True, blank=True,
            related_name="reverse_make_depends", symmetrical=False)
    replaces = models.ManyToManyField('self', null=True, blank=True,
            related_name='reverse_replaces', symmetrical=False)
    conflicts = models.ManyToManyField('self', null=True, blank=True,
            related_name="reverse_conflicts", symmetrical=False)
    provides = models.ManyToManyField(Provision, null=True, blank=True)
    deleted = models.BooleanField(default=False)
    outdated = models.BooleanField(default=False)
    added = models.DateTimeField(editable=False, default=datetime.now)
    updated = models.DateTimeField(editable=False)
    groups = models.ManyToManyField(Group, null=True, blank=True)

    def __unicode__(self):
        return u'%s %s' % (self.name, self.version)

    def get_arch(self):
        return ', '.join(map(smart_unicode, self.architectures.all()))
    get_arch.short_description = 'architectures'

    def get_tarball_basename(self):
        """Return the basename of the absolute path to the tarball"""
        return os.path.basename(self.tarball.path)

    def get_absolute_url(self):
        return ('aur-package_detail', [self.slug,])
    get_absolute_url = permalink(get_absolute_url)

    def save(self):
        self.updated = datetime.now()
        if not self.slug:
            import re
            slug = re.sub('[^\w\s-]', '', self.name).strip().lower()
            slug = re.sub('[-\s]+', '-', slug)
            self.slug = slug
        super(Package, self).save()

    class Meta:
        ordering = ('-updated',)
        get_latest_by = 'updated'


class PackageFile(models.Model):
    package = models.ForeignKey(Package)
    # filename for local sources and url for external
    filename = models.FileField(upload_to=_get_package_upload_to, null=True, blank=True)
    url = models.URLField(null=True, blank=True)

    def get_absolute_url(self):
        if self.filename:
            return self.filename.url
        else:
            return self.url

    def get_filename(self):
        if self.filename:
            return os.path.basename(self.filename.path)
        else:
            return self.url

    def __unicode__(self):
        return self.filename

class PackageHash(models.Model):
    # sha512 hashes are 128 characters
    hash = models.CharField(max_length=128, primary_key=True)
    type = models.CharField(max_length=12)
    file = models.ForeignKey(PackageFile)

    def __unicode__(self):
        return self.hash

    class Meta:
        verbose_name_plural = 'package hashes'


class Comment(models.Model):
    package = models.ForeignKey(Package)
    parent = models.ForeignKey('self', null=True, blank=True)
    user = models.ForeignKey(User)
    message = models.TextField()
    added = models.DateTimeField(editable=False, default=datetime.now)
    ip = models.IPAddressField()
    hidden = models.BooleanField(default=False)

    def __unicode__(self):
        return self.message


class PackageNotification(models.Model):
    user = models.ForeignKey(User)
    package = models.ForeignKey(Package)

    def __unicode__(self):
        return u"%s's subscription to %s updates" % (self.user.username,
                self.package.name)


class Vote(models.Model):
    user = models.ForeignKey(User)
    package = models.ForeignKey(Package)
    added = models.DateTimeField(default=datetime.now)

    def __unicode__(self):
        return u"%s's vote for %s" % (self.user.username, self.package.name)

    class Meta:
        unique_together = (("user", "package"),)


# Should this be here?
def email_package_updates(sender, instance, signal, *args, **kwargs):
    from django.conf import settings
    """Send notification to users of modification to a Package"""
    subject = "Archlinux AUR: %s updated" % instance.name
    mail_list = []
    notifications = PackageNotification.objects.filter(package=instance)
    for notification in notifications:
        if not notification.user.email:
            continue
        message = render_to_string('aur/email_notification.txt', {
            'package': instance,
            'user': notification.user,
        })
        mail_list.append((subject, message, settings.DEFAULT_FROM_EMAIL,
            (notification.user.email,)))
    return send_mass_mail(mail_list)


def remove_packagefile_filename(sender, instance, signal, *args, **kwargs):
    """Remove PackageFile's file"""
    if instance.filename:
        instance.filename.delete()

def remove_package_tarball(sender, instance, signal, *args, **kwargs):
    """Remove Package's tarball"""
    instance.tarball.delete()

# Send notifications of updates to users on saves and deltion of packages
signals.post_save.connect(email_package_updates, sender=Package)
signals.post_delete.connect(email_package_updates, sender=Package)
# Remove files when packages get deleted
# Django doesn't call each instance's delete() on cascade, but it does send
# pre_delete signals
signals.pre_delete.connect(remove_packagefile_filename, sender=PackageFile)
signals.pre_delete.connect(remove_package_tarball, sender=Package)

