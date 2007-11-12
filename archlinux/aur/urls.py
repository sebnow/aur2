from django.conf.urls.defaults import *
from archlinux.aur.models import Package

detail_dict = {
    'queryset': Package.objects.all(),
    'template_object_name': 'pkg',
}

urlpatterns = patterns('',
    (r'^$', 'archlinux.aur.views.search'),
    (r'^search/$', 'archlinux.aur.views.search'),
    (r'^submit/$', 'archlinux.aur.views.submit'),
)

# Generic views
# These will probably be removed at a later stage
urlpatterns += patterns('django.views.generic',
    (r'^package/(?P<object_id>\w+)/$', 'list_detail.object_detail', dict(detail_dict)),
)
