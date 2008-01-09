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
    url(r'^package/(?P<object_id>[\w_-]+)/notify_of_updates/$',
        'notify_of_updates', name='aur-notify_of_updates'),
    url(r'^package/(?P<object_id>[\w_-]+)/denotify_of_updates/$',
        'denotify_of_updates', name='aur-denotify_of_updates'),
    (r'^api/search/(?P<query>[\w\d_ -]+)/$', 'api_search'),
    (r'^api/get_package_info/(?P<object_id>[\w_-]+)/$', 'api_package_info'),
    (r'^api/get_package_comments/(?P<object_id>[\w_-]+)/$', 'api_package_comments'),
)

# Generic views
# These will probably be removed at a later stage
urlpatterns += patterns('django.views.generic',
    (r'^package/(?P<object_id>[\w_-]+)/$', 'list_detail.object_detail',
        dict(detail_dict), 'aur-package_detail'),
)
