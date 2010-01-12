from django.conf.urls.defaults import *
from piston.resource import Resource
from piston.authentication import HttpBasicAuthentication
from archlinux.aur.api.handlers import PackageInfoHandler

auth = HttpBasicAuthentication(realm='AUR API')
package_info_handler = Resource(handler=PackageInfoHandler, authentication=auth)

urlpatterns = patterns('',
    url(r'^packages\.(?P<emitter_format>[a-zA-Z]+)$', package_info_handler),
    url(r'^packages$', package_info_handler, {'emitter_format' : 'json'}),
    url(r'^package/(?P<object_id>[\w_-]+)\.(?P<emitter_format>[a-zA-Z]+)$', package_info_handler),
    url(r'^package/(?P<object_id>[\w_-]+)$', package_info_handler,
        {'emitter_format' : 'json'}),
)

