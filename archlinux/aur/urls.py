from django.conf.urls.defaults import *
from archlinux.aur.models import Package

detail_dict = {
    'queryset': Package.objects.all(),
    'template_object_name': 'pkg',
}

urlpatterns = patterns('archlinux.aur.views',
    url(r'^$', 'search', name='aur-main'),
    url(r'^search/$', 'search', name='aur-search'),
    url(r'^submit/$', 'submit', name='aur-submit_package'),
    url(r'^package/(?P<object_id>[\w_-]+)/comment/$', 'comment',
        name='aur-comment_on_package'),
    url(r'^package/(?P<object_id>[\w_-]+)/flag_out_of_date/$',
        'flag_out_of_date', name='aur-flag_out_of_date'),
)

# Generic views
# These will probably be removed at a later stage
urlpatterns += patterns('django.views.generic',
    (r'^package/(?P<object_id>[\w_-]+)/$', 'list_detail.object_detail',
        dict(detail_dict), 'aur-package_detail'),
)
