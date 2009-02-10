from django.conf.urls.defaults import *
from django.contrib import admin
from django.conf import settings

admin.autodiscover()

urlpatterns = patterns('',
    (r'^admin/(.*)', admin.site.root),
    (r'^accounts/', include('registration.urls')),
    (r'^profile/', include('aurprofile.urls')),
    (r'^', include('archlinux.aur.urls')),
)

if settings.DEBUG == True:
	urlpatterns += patterns('',
		(r'^media/(.*)$', 'django.views.static.serve', {
		    'document_root': settings.MEDIA_ROOT
		})
	)
