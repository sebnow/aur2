from django.conf.urls.defaults import *
from django.contrib import admin
from django.conf import settings

from aur.feeds import RssLatestPackages

admin.autodiscover()

feeds_packages = {
    'rss': RssLatestPackages
}

urlpatterns = patterns('',
    (r'^admin/(.*)', admin.site.root),
    (r'^accounts/', include('registration.urls')),
    (r'^profile/', include('aurprofile.urls')),
    (r'^', include('aur.urls')),
    (r'^feeds/(?P<url>.*)/packages/$', 'django.contrib.syndication.views.feed',
        {'feed_dict': feeds_packages}),
)

if settings.DEBUG == True:
	urlpatterns += patterns('',
		(r'^media/(.*)$', 'django.views.static.serve', {
		    'document_root': settings.MEDIA_ROOT
		})
	)
