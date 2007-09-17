from django.conf.urls.defaults import *

urlpatterns = patterns('',
    # Example:
    # (r'^archlinux/', include('archlinux.foo.urls')),

    # Uncomment this for admin:
    (r'^admin/', include('django.contrib.admin.urls')),
    (r'^', include('archlinux.aur.urls')),
)
