from django.conf.urls.defaults import *
from archlinux.aur.models import Package

detail_dict = {
    'queryset': Package.objects.all(),
    'template_object_name': 'pkg',
}

urlpatterns = patterns('archlinux.aur.views',
    (r'^$', 'search'),
    (r'^search/$', 'search'),
    (r'^submit/$', 'submit'),
    (r'^package/(?P<object_id>\w+)/comment/$', 'comment'),
)

# Generic views
# These will probably be removed at a later stage
urlpatterns += patterns('django.views.generic',
    (r'^package/(?P<object_id>[\w-]+)/$', 'list_detail.object_detail', dict(detail_dict), 'package-detail'),
)
