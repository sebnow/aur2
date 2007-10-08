from django.conf.urls.defaults import *

urlpatterns = patterns('',
    # Example:
    # (r'^archlinux/', include('archlinux.foo.urls')),

    # Uncomment this for admin:
    (r'^admin/', include('django.contrib.admin.urls')),
    url(r'^accounts/logout/', 'django.contrib.auth.views.logout', name='user_logout'),
    url(r'^accounts/login/', 'django.contrib.auth.views.login', name='user_login'),
    (r'^', include('archlinux.aur.urls')),
)
