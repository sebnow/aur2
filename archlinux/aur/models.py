from django.db import models
from django.db import transaction
from django.contrib.auth.models import User
from django.core.mail import send_mass_mail
from django.db.models import signals, permalink
from django.dispatch import dispatcher
from django.template.loader import render_to_string
from django.utils.encoding import smart_unicode

from datetime import datetime
import os


class Category(models.Model):
    name = models.CharField(max_length=20)

    def __unicode__(self):
        return self.name

    class Admin:
        pass

    class Meta:
        verbose_name_plural = 'categories'


class Architecture(models.Model):
    name = models.CharField(max_length=10)

    def __unicode__(self):
        return self.name

    class Admin:
        pass


class Repository(models.Model):
    name = models.CharField(max_length=20)

    def __unicode__(self):
        return self.name

    class Admin:
        pass

    class Meta:
        verbose_name_plural = 'repositories'


class License(models.Model):
    name = models.CharField(max_length=24)

    def __unicode__(self):
        return self.name

    class Admin:
        pass


class Group(models.Model):
    name = models.CharField(max_length=10)

    def __unicode__(self):
        return self.name

    class Admin:
        pass


class Package(models.Model):
    name = models.CharField(primary_key=True, max_length=30)
    version = models.CharField(max_length=20)
    release = models.SmallIntegerField()
    description = models.CharField(max_length=180)
    url = models.CharField(max_length=200, null=True, blank=True)
    maintainers = models.ManyToManyField(User)
    repository = models.ForeignKey(Repository)
    category = models.ForeignKey(Category)
    tarball = models.FileField(upload_to='packages')
    licenses = models.ManyToManyField(License, null=True, blank=True)
    architectures = models.ManyToManyField(Architecture)
    depends = models.ManyToManyField('self', null=True, blank=True,
            related_name="reverse_depends", symmetrical=False)
    make_depends = models.ManyToManyField('self', null=True, blank=True,
            related_name="reverse_make_depends", symmetrical=False)
    provides = models.ManyToManyField('self', null=True, blank=True,
            related_name="reverse_provides", symmetrical=False)
    replaces = models.ManyToManyField('self', null=True, blank=True,
            related_name="reverse_replaces", symmetrical=False)
    conflicts = models.ManyToManyField('self', null=True, blank=True,
            related_name="reverse_conflicts", symmetrical=False)
    deleted = models.BooleanField(default=False)
    outdated = models.BooleanField(default=False)
    added = models.DateTimeField(editable=False, default=datetime.now())
    updated = models.DateTimeField()
    groups = models.ManyToManyField(Group, null=True, blank=True)

    def __unicode__(self):
        return u'%s %s' % (self.name, self.version)

    def get_arch(self):
        return ', '.join(map(smart_unicode, self.architectures.all()))
    get_arch.short_description = 'architectures'

    def get_tarball_basename(self):
        """Return the basename of the absolute path to the tarball"""
        return os.path.basename(self.get_tarball_filename())

    def get_absolute_url(self):
        return ('aur-package_detail', [self.name,])
    get_absolute_url = permalink(get_absolute_url)

    def save(self):
        self.updated = datetime.now()
        super(Package, self).save()

    def delete_tarball(self):
        """Remove Package's tarball"""
        os.remove(self.get_tarball_filename())
        os.rmdir(os.path.dirname(self.get_tarball_filename()))

    def _save_FIELD_file(self, field, filename, raw_contents, save=True):
        old_upload_to=field.upload_to
        dirname, filename = filename.rsplit(os.path.sep, 1)
        field.upload_to = os.path.join(field.upload_to, dirname)
        super(Package, self)._save_FIELD_file(field, filename,
                raw_contents, save)
        field.upload_to = old_upload_to

    class Admin:
        list_display = ('name', 'category', 'get_arch', 'updated')

    class Meta:
        ordering = ('-updated',)
        get_latest_by = 'updated'


class PackageFile(models.Model):
    package = models.ForeignKey(Package)
    # filename for local sources and url for external
    filename = models.FileField(upload_to='packages', null=True, blank=True)
    url = models.URLField(null=True, blank=True)

    def get_absolute_url(self):
        if self.filename:
            return self.get_filename_url()
        else:
            return self.url

    def get_filename(self):
        if self.filename:
            return os.path.basename(self.get_filename_filename())
        else:
            return self.url

    def _save_FIELD_file(self, field, filename, raw_contents, save=True):
        old_upload_to=field.upload_to
        dirname, filename = filename.rsplit(os.path.sep, 1)
        field.upload_to = os.path.join(field.upload_to, dirname)
        super(PackageFile, self)._save_FIELD_file(field, filename,
                raw_contents, save)
        field.upload_to = old_upload_to

    def __unicode__(self):
        return self.filename

    class Admin:
        pass

class PackageHash(models.Model):
    # sha512 hashes are 128 characters
    hash = models.CharField(max_length=128, primary_key=True)
    type = models.CharField(max_length=12)
    file = models.ForeignKey(PackageFile)

    def __unicode__(self):
        return self.hash

    class Meta:
        verbose_name_plural = 'package hashes'

    class Admin:
        pass


class Comment(models.Model):
    package = models.ForeignKey(Package)
    parent = models.ForeignKey('self', null=True, blank=True)
    user = models.ForeignKey(User)
    message = models.TextField()
    added = models.DateTimeField(editable=False, default=datetime.now())
    ip = models.IPAddressField()
    hidden = models.BooleanField(default=False)

    def __unicode__(self):
        return self.message

    class Admin:
        pass


class PackageNotification(models.Model):
    user = models.ForeignKey(User)
    package = models.ForeignKey(Package)

    def __unicode__(self):
        return u"%s's subscription to %s updates" % (self.user.username,
                self.package.name)

    class Admin:
        pass


# Should this be here?
def email_package_updates(sender, instance, signal, *args, **kwargs):
    """Send notification to users of modification to a Package"""
    subject = "Archlinux AUR: %s updated" % instance.name
    sender = 'xilon'
    mail_list = []
    notifications = PackageNotification.objects.filter(package=instance)
    for notification in notifications:
        message = render_to_string('aur/email_notification.txt', {
            'package': instance,
            'user': notification.user,
        })
        mail_list.append((subject, message, sender,
            (notification.user.email,)))
    return send_mass_mail(mail_list)


def remove_packagefile_filename(sender, instance, signal, *args, **kwargs):
    """Remove PackageFile's file"""
    if instance.filename:
        os.remove(instance.get_filename_filename())
        try:
            os.rmdir(os.path.dirname(instance.get_filename_filename()))
        except:
            pass


def remove_package_tarball(sender, instance, signal, *args, **kwargs):
    """Remove Package's tarball"""
    instance.delete_tarball()

# Send notifications of updates to users on saves and deltion of packages
dispatcher.connect(email_package_updates, signal=signals.post_save,
        sender=Package)
dispatcher.connect(email_package_updates, signal=signals.post_delete,
        sender=Package)
# Remove files when packages get deleted
# Django doesn't call each instance's delete() on cascade, but it does send
# pre_delete signals
dispatcher.connect(remove_packagefile_filename, signal=signals.pre_delete,
        sender=PackageFile)
dispatcher.connect(remove_package_tarball, signal=signals.pre_delete,
        sender=Package)
