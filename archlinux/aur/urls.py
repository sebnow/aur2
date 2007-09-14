from django.conf.urls.defaults import *
from archlinux.aur.models import Package

info_dict = {
    'queryset': Package.objects.all(),
    'date_field': 'updated',
}

urlpatterns = patterns('django.views.generic',
    (r'^/?$', 'date_based.archive_index', info_dict),
)
