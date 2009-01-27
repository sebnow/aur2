from django.conf.urls.defaults import *
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Example:
    # (r'^archlinux/', include('archlinux.foo.urls')),

    # Uncomment this for admin:
    (r'^admin/(.*)', admin.site.root),
    (r'^accounts/', include('archlinux.account.urls')),
    (r'^', include('archlinux.aur.urls')),
)
