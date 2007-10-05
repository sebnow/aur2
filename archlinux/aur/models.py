from django.db import models
from django.contrib.admin.models import User
from django import newforms as forms # This will change to forms in 0.98 or 1.0

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


class Package(models.Model):
    name = models.CharField(primary_key=True, max_length=30)
    version = models.CharField(max_length=20)
    release = models.SmallIntegerField()
    description = models.CharField(max_length=180)
    maintainers = models.ManyToManyField(User)
    repository = models.ForeignKey(Repository)
    category = models.ForeignKey(Category)
    architecture = models.ManyToManyField(Architecture)
    dep_packages = models.ManyToManyField('self', null=True, blank=True)
    deleted = models.BooleanField()
    added = models.DateTimeField()
    updated = models.DateTimeField()

    def __unicode__(self):
        return self.name

    def get_arch(self):
        return ', '.join(map(str, self.architecture.all()))
    get_arch.short_description = 'architectures'

    class Admin:
        list_display = ('name', 'category', 'get_arch', 'updated')

    class Meta:
        ordering = ('-updated',)
        get_latest_by = 'updated'

class PackageFile(models.Model):
    package = models.ForeignKey(Package)
    filename = models.CharField(max_length=100)

class PackageHash(models.Model):
    package = models.ForeignKey(Package)
    type = models.IntegerField()
    hash = models.CharField(max_length=64)

    def __unicode__(self):
        return self.hash

    class Meta:
        verbose_name_plural = 'packagehashes'


class Comment(models.Model):
    package = models.ForeignKey(Package)
    parent = models.ForeignKey('self', null=True, blank=True)
    user = models.ForeignKey(User)
    message = models.TextField()
    added = models.DateTimeField()
    ip = models.IPAddressField()
    hidden = models.BooleanField()
    commit = models.BooleanField()

    def __unicode__(self):
        return self.message

    class Admin:
        pass


class PackageSearchForm(forms.Form):
    query = forms.CharField(max_length=30)
    repository = forms.CharField(max_length=20)
    category = forms.CharField(max_length=20)
    lastupdate = forms.DateTimeField()
    limit = forms.ChoiceField(choices=(
        (25, 25),
        (50, 50),
        (75, 75),
        (100, 100),
        (150, 150),
    ))
    sortby = forms.ChoiceField(choices=(
        ('name', 'Package Name'),
        ('category', 'Category'),
        ('location', 'Location'),
        ('votes', 'Votes'),
        ('maintainer', 'Maintainer'),
        ('age', 'Age'),
    ))
    order = ChoiceField(choices=(
        ('asc', 'Ascending'),
        ('desc', 'Descending'),
    ))
    searchby = forms.ChoiceField(choices=(
        ('name': 'Package Name'),
        ('maintainer': 'Maintainer'),
    ))
