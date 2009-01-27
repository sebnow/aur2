from django.db import models
from django.contrib.auth.models import User
from django.utils.encoding import smart_unicode
from archlinux.aur.models import Package

class ArchUser(models.Model):
    user = models.ForeignKey(User, unique=True)
    is_inactive = models.BooleanField(default=False)
    irc_nick = models.CharField(max_length=16)

    def get_packages(self):
        return Package.objects.filter(maintainers__username=self.user.username)

    def can_modify_package(self, package):
        if not isinstance(package, Package):
            package = Package.objects.get(name=package)
        return self.is_maintainer(package) or self.is_moderator()

    def can_delete_package(self, package):
        return self.is_moderator()

    def is_maintainer(self, package):
        if not isinstance(package, Package):
            package = Package.objects.get(name=package)
        return package.maintainers.filter(username=self.user.username).count() > 0

    def is_moderator(self):
        is_trusted_user = self.user.groups.filter(name="Trusted User").count() > 0
        is_developer = self.user.groups.filter(name="Developer").count() > 0
        return is_trusted_user or is_developer

    def __unicode__(self):
        return smart_unicode(self.user)

