from django.conf.urls.defaults import *
from archlinux.aur.models import Package

index_dict = {
    'queryset': Package.objects.all(),
    'date_field': 'updated',
}

detail_dict = {
    'queryset': Package.objects.all(),
    'template_object_name': 'pkg',
}

urlpatterns = patterns('',
    (r'^$', 'archlinux.aur.views.search'),
    (r'^search/$', 'archlinux.aur.views.search'),
)

# Generic views
# These will probably be removed at a later stage
urlpatterns += patterns('django.views.generic',
    (r'^package/(?P<object_id>\w+)/$', 'list_detail.object_detail', dict(detail_dict)),
)
