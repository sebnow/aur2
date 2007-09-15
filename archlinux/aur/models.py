from django.db import models
from django.contrib.admin.models import User

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


class Package(models.Model):
    name = models.CharField(max_length=30)
    description = models.CharField(max_length=180)
    maintainers = models.ManyToManyField(User)
    category = models.ForeignKey(Category)
    architecture = models.ManyToManyField(Architecture)
    dep_packages = models.ManyToManyField('self', null=True, blank=True)
    deleted = models.BooleanField()
    added = models.DateTimeField()
    updated = models.DateTimeField()

    def __unicode__(self):
        return self.name

    def get_arch(self):
        return self.architecture.all()

    class Admin:
        list_display = ('name', 'category', 'get_arch', 'updated')

    class Meta:
        ordering = ('-updated',)
        get_latest_by = 'updated'

class PackageFile(models.Model):
    package = models.ForeignKey(Package)
    filename = models.CharField(100)

