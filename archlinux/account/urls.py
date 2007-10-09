from django.conf.urls.defaults import *

urlpatterns = patterns('',
    url(r'^logout/$', 'django.contrib.auth.views.logout', name='user_logout'),
    url(r'^login/$', 'django.contrib.auth.views.login', name='user_login'),
    (r'^register/$', 'archlinux.account.views.register'),
    (r'^profile/$', 'archlinux.account.views.profile'),
    (r'^profile/update/$', 'archlinux.account.views.update_profile'),
)
