from django.db import models
from django.contrib.admin.models import User
from django import newforms as forms # This will change to forms in 0.98 or 1.0
from django.core.mail import send_mass_mail
from django.db.models import signals, permalink
from django.dispatch import dispatcher

from django.template.loader import render_to_string

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

    def get_absolute_url(self):
        return ('aur-package_detail', [self.name,])
    get_absolute_url = permalink(get_absolute_url)

    def save(self):
        self.updated = datetime.now()
        super(Package, self).save()

    class Admin:
        list_display = ('name', 'category', 'get_arch', 'updated')

    class Meta:
        ordering = ('-updated',)
        get_latest_by = 'updated'


class PackageFile(models.Model):
    package = models.ForeignKey(Package)
    # filename for local sources and url for external
    filename = models.FileField(upload_to='packages/', null=True, blank=True)
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
        field.upload_to = os.path.join(field.upload_to, os.path.dirname(filename))
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
    commit = models.BooleanField(default=False)

    def __unicode__(self):
        return self.message

    class Admin:
        pass


class PackageNotification(models.Model):
    user = models.ForeignKey(User)
    package = models.ForeignKey(Package)

    def __unicode__(self):
        return "%s subscription to %s updates" % (self.user.username, self.package.name)

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

class PackageSubmitForm(forms.Form):
    # Borrowed from AUR2-BR
    def __init__(self, *args, **kwargs):
        super(PackageSubmitForm, self).__init__(*args, **kwargs)
        category_choices = [(category.name.lower(), category.name) for category in Category.objects.all()]
        self.fields['category'].choices = category_choices

    category = forms.ChoiceField(choices=())
    file = forms.FileField(label="PKGBUILD")
    comment = forms.CharField(widget=forms.Textarea, label="Commit Message")

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

# Send notifications of updates to users on saves and deltion of packages
dispatcher.connect(email_package_updates, signal=signals.post_save,
        sender=Package)
dispatcher.connect(email_package_updates, signal=signals.post_delete,
        sender=Package)
