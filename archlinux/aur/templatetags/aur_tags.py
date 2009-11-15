from django.template import Library
from django.template.defaultfilters import stringfilter
from django.contrib.auth.models import User
from aur.models import Package, PackageNotification
import re

register = Library()

@register.filter
def has_update_notification(user, package):
    if not isinstance(user, User):
        return False
    total = PackageNotification.objects.filter(user=user,
        package=package).count()
    return total != 0

@register.filter
@stringfilter
def merge_query_string(url, query_string):
    """Merge two query strings"""
    new_url = url
    query_bits = query_string.split('&')
    for query_bit in query_bits:
        key, value = query_bit.split('=', 1)
        # Check if the variable is set in the url
        if url.find(key) >= 0:
            # Substitute existing value
            new_url = re.sub('(%s)=([A-Za-z0-9_+-]+)' % key, '\\1=%s' % value, new_url)
        else:
            # Append new key-value pair
            new_url = "".join([new_url, "&%s=%s" % (key, value)])
    return new_url
