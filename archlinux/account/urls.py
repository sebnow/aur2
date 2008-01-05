from django.conf.urls.defaults import *

urlpatterns = patterns('',
    url(r'^logout/$', 'django.contrib.auth.views.logout',
        name='account-logout'),
    url(r'^login/$', 'django.contrib.auth.views.login',
        name='account-login'),
    url(r'^register/$', 'archlinux.account.views.register',
        name='account-register'),
    url(r'^profile/$', 'archlinux.account.views.profile',
        name='account-my_profile'),
    url(r'^profile/update/$', 'archlinux.account.views.update_profile',
        name='account-update_profile'),
)
