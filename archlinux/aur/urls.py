from django.conf.urls.defaults import *
from archlinux.aur.models import Package

info_dict = {
    'queryset': Package.objects.all(),
    'date_field': 'updated',
}

urlpatterns = patterns('django.views.generic',
    (r'^package/(?P<object_id>[a-zA-Z0-9_]+)/$', 'list_detail.object_detail',
        dict(queryset=Package.objects.all(), template_object_name='pkg')),
    (r'^$', 'date_based.archive_index', info_dict),
)
