from django.db import models
from django.db import transaction
from django.contrib.admin.models import User
from django import newforms as forms # This will change to forms in 0.98 or 1.0
from django.core.mail import send_mass_mail
from django.db.models import signals, permalink
from django.dispatch import dispatcher
from django.utils.translation import ugettext
from django.template.loader import render_to_string

from datetime import datetime
import os
import sys

import archlinux.aur.Package as PKGBUILD

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
        return "%s %s" % (self.name, self.version)

    def get_arch(self):
        return ', '.join(map(str, self.architectures.all()))
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
        return "%s's subscription to %s updates" % (self.user.username,
                self.package.name)

    class Admin:
        pass

class PackageSearchForm(forms.Form):
    # Borrowed from AUR2-BR
    def __init__(self, *args, **kwargs):
        super(PackageSearchForm, self).__init__(*args, **kwargs)
        category_choices = [('all', 'All')]
        category_choices += [(category.name.lower(), category.name) for category in Category.objects.all()]
        repository_choices = [('all', 'All')]
        repository_choices += [(repository.name.lower(), repository.name) for repository in Repository.objects.all()]
        self.fields['category'].choices = category_choices
        self.fields['repository'].choices = repository_choices

    repository = forms.ChoiceField(initial='all', choices=())
    category = forms.ChoiceField(initial='all', choices=())
    query = forms.CharField(max_length=30, label="Keywords", required=False)
    searchby = forms.ChoiceField(initial='name', label="Search By",choices=(
        ('name', 'Package Name'),
        ('maintainer', 'Maintainer'),
    ))
    lastupdate = forms.DateTimeField(label="Last Update", required=False)
    sortby = forms.ChoiceField(initial='name', label="Sort By", choices=(
        ('name', 'Package Name'),
        ('category', 'Category'),
        ('repository', 'Repository'),
        ('updated', 'Last Updated'),
    ))
    order = forms.ChoiceField(initial='asc', choices=(
        ('asc', 'Ascending'),
        ('desc', 'Descending'),
    ))
    limit = forms.ChoiceField(initial='25', choices=(
        (25, 25),
        (50, 50),
        (75, 75),
        (100, 100),
        (150, 150),
    ))

    def get_or_default(self, key):
        if not self.is_bound:
            return self.fields[key].initial
        return self.cleaned_data.get(key, self.fields[key].initial)

    def search(self):
        if self.is_bound and not self.is_valid():
            return None
        repository = self.get_or_default('repository')
        lastupdate = self.get_or_default('lastupdate')
        category = self.get_or_default('category')
        sortby = self.get_or_default('sortby')
        order = self.get_or_default('order')

        # Find the packages by searching description and package name or maintainer
        if self.get_or_default('query'):
            if self.get_or_default('searchby') == 'maintainer':
                results = Package.objects.filter(maintainers__username__icontains=self.cleaned_data["query"])
            else:
                res1 = Package.objects.filter(name__icontains=self.cleaned_data["query"])
                res2 = Package.objects.filter(description__icontains=self.cleaned_data["query"])
                results = res1 | res2
        else:
            results = Package.objects.all()
        # Restrict results
        if repository != 'all':
            results = results.filter(repository__name__iexact=repository)
        if category != 'all':
            results = results.filter(category__name__exact=category)
        if lastupdate:
            results = results.filter(updated__gte=lastupdate)
        # Change the sort order if necessary
        if order == 'desc':
            results = results.order_by('-' + sortby, 'repository', 'category', 'name')
        else:
            results = results.order_by(sortby, 'repository', 'category', 'name')
        return results

class PackageField(forms.FileField):
    widget = forms.widgets.FileInput
    def __init__(self, *args, **kwargs):
        super(forms.FileField, self).__init__(*args, **kwargs)

    def clean(self, data):
        import tempfile
        import tarfile
        try:
            file = super(PackageField, self).clean(data)
        except:
            raise
        errors = list()
        # Save the uploaded file to disk
        directory = tempfile.mkdtemp()
        filename = os.path.join(directory, file.filename)
        fp = open(filename, "wb")
        fp.write(file.content)
        fp.close()

        # Try to parse the PKGBUILD
        try:
            pkg = PKGBUILD.Package(filename)
        except:
            raise forms.ValidationError(sys.exc_info()[1])
        # Add path of the tarball/PKGBUILD so we can reference in other places
        pkg['filename'] = filename
        # Validate PKGBUILD
        pkg.validate()
        if not pkg.is_valid() or pkg.has_warnings():
            errors.extend(pkg.get_errors())
            errors.extend(pkg.get_warnings())
        # Check if we have everything we need
        for arch in pkg['arch']:
            try:
                Architecture.objects.get(name=arch)
            except Architecture.DoesNotExist:
                errors.append('architecture %s does not exist' % arch)
        if pkg['install']:
            try:
                tar = tarfile.open(filename)
            except tarfile.ReadError:
                errors.append('install files are missing')
            else:
                files = tar.getnames()
                for file in pkg['install']:
                    filepath = os.path.join(pkg['name'], file)
                    if not filepath in files:
                        errors.append('install file "%s" is missing' % file)
                del files
        # Report errors or return the validated package
        if errors:
            raise forms.ValidationError(errors)
        else:
            return pkg

class PackageSubmitForm(forms.Form):
    category = forms.ChoiceField(choices=())
    package = PackageField(label="PKGBUILD")

    # Borrowed from AUR2-BR
    def __init__(self, *args, **kwargs):
        super(PackageSubmitForm, self).__init__(*args, **kwargs)
        category_choices = [(category.name.lower(), category.name) for category in Category.objects.all()]
        self.fields['category'].choices = category_choices

    @transaction.commit_manually
    def save(self, user):
        import hashlib
        import tarfile
        pkg = self.cleaned_data['package']
        tmpdir = os.path.dirname(pkg['filename'])
        package = Package(name=pkg['name'],
                version=pkg['version'],
                release=pkg['release'],
                description=pkg['description'],
                url=pkg['url'])
        package.repository=Repository.objects.get(name="Unsupported")
        package.category=Category.objects.get(name=self.cleaned_data['category'])
        # Save the package so we can reference it
        package.save()
        package.maintainers.add(user)
        # Check for, and add dependencies
        for dependency in pkg['depends']:
            # This would be nice, but we don't have access to the official
            # repositories
            try:
                dep = Package.objects.get(name=dependency)
            except Package.DoesNotExist:
                # Fail silently
                pass
            else:
                package.depends.add(dep)
        # Add licenses
        for license in pkg['licenses']:
            object, created = License.objects.get_or_create(name=license)
            package.licenses.add(object)
        # Add architectures
        for arch in pkg['arch']:
            object = Architecture.objects.get(name=arch)
            package.architectures.add(object)
        # Check if the uploaded file is a tar file or just a PKGBUILD
        try:
            tar = tarfile.open(pkg['filename'], "r")
        except tarfile.ReadError:
            # It's not a tar file, so if must be a PKGBUILD since it validated
            is_tarfile = False
            pkgbuild = pkg['filename']
        else:
            is_tarfile = True
            tmpdir_sources = os.path.join(tmpdir, 'sources')
            tar.extractall(tmpdir_sources)
            pkgbuild = os.path.join(tmpdir_sources, pkg['name'], 'PKGBUILD')
        # Hash and save PKGBUILD
        fp = open(pkgbuild, "r")
        pkgbuild_contents = ''.join(fp.readlines())
        fp.close()
        source = PackageFile(package=package)
        source.save_filename_file('%s/sources/PKGBUILD' % pkg['name'],
                pkgbuild_contents)
        source.save()
        md5hash = hashlib.md5(pkgbuild_contents)
        hash = PackageHash(hash=md5hash.hexdigest(), file=source, type='md5')
        hash.save()
        del pkgbuild_contents
        # Save tarball
        # TODO: Tar the saved sources instead of using the uploaded one, for
        # security
        if not is_tarfile:
            # We only have the PKGBUILD, so lets make a tarball
            tar = tarfile.open(os.path.join(tmpdir, '%s.tar.gz' % pkg['name']),
                    "w|gz")
            tar.add(pkg['filename'], '%s/PKGBUILD' % pkg['name'])
            tar.close()
            pkg['filename'] = os.path.join(tmpdir, '%s.tar.gz' % pkg['name'])
        fp = open(pkg['filename'], "rb")
        package.save_tarball_file('%s/%s' % (pkg['name'],
            os.path.basename(pkg['filename'])), ''.join(fp.readlines()))
        fp.close()
        # Save source files
        for index in range(len(pkg['source'])):
            source_filename = pkg['source'][index]
            source = PackageFile(package=package)
            # If it's a local file, save to disk, otherwise record as url
            if is_tarfile and os.path.exists(os.path.join(tmpdir_sources,
               package.name, source_filename)):
                    fp = open(os.path.join(tmpdir_sources, pkg['name'],
                        source_filename), "r")
                    source.save_filename_file('%s/sources/%s' % (pkg['name'],
                        source_filename), ''.join(fp.readlines()))
                    fp.close()
            else:
                # TODO: Check that it _is_ a url, otherwise report an error
                # that files are missing
                source.url = source_filename
            source.save()
            # Check for, and save, any hashes this file may have
            for hash_type in ('md5', 'sha1', 'sha256', 'sha384', 'sha512'):
                if pkg[hash_type + 'sums']:
                    PackageHash(hash=pkg[hash_type + 'sums'][index],
                            file=source, type=hash_type).save()
        # Save install files
        for file in pkg['install']:
            source = PackageFile(package=package)
            source_path = os.path.join(tmpdir_sources, pkg['name'], file)
            fp = open(source_path, "r")
            source.save_filename_file('%s/install/%s' % (pkg['name'], file),
                    ''.join(fp.readlines()))
            fp.close()
            source.save()
        transaction.commit()
        # Remove temporary files
        for root, dirs, files in os.walk(tmpdir, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        os.rmdir(tmpdir)


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
    os.remove(instance.get_tarball_filename())
    os.rmdir(os.path.dirname(instance.get_tarball_filename()))


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
