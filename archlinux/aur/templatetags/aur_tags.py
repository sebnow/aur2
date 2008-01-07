from django.template import Library
from django.contrib.auth.models import User
from archlinux.aur.models import Package, PackageNotification

register = Library()

@register.filter
def has_update_notification(user, package_pk):
    if not isinstance(user, User):
        return False
    total = PackageNotification.objects.filter(user__username=user,
            package=package_pk).count()
    return total != 0
