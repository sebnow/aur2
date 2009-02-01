from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('aurprofile.views',
    url(r'^$', 'profile', name='aurprofile_profile'),
)
