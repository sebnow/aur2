import time
import urlparse
from piston.handler import BaseHandler, AnonymousBaseHandler
from piston.utils import rc
from django.shortcuts import get_object_or_404
from django.contrib.sites.models import Site
from archlinux.aur.models import Package

# Fields of interest when retrieving package information via the API.
pkg_info_fields = ('name', 'version', 'release', 'description', 'url',
          'maintainers', 'repository', 'tags', 'tarball',
          'licenses', 'architectures', 'depends', 'make_depends',
          'replaces', 'conflicts', 'provides', 'deleted', 'outdated',
          'added', 'updated', 'groups',
          'sources', 'md5', 'sha1', 'permalink', 'comments')

# A helper function.
def get_hashes(pkg, hash_type):
    """Return the hashes of a package's source files, where each hash
    must be of hash_type.  hash_type is presently one of md5 or sha1."""
    return [x.hash
            for y in pkg.packagefile_set.all()
            for x in y.packagehash_set.filter(type=hash_type)]

class BasePackageInfoHandler(BaseHandler):
    """Defines methods shared between PackageInfoHandler and
    AnonymousPackageInfoHandler."""

# Piston gives us some flexibility when sending objects to a client via
# the API.  By default, it will represent foreign key and many-to-many
# fields with nested objects.  E.G.,
# the maintainers field of Package might be represented like this:
# "maintainers" : [{"username" : "joe"}, {"username" : "Bob"} ...]
# But the following is a nicer representation:
# "maintainers" : ["joe", "bob"].
# We can use resource methods to generate the contents of an object's
# fields.  In this case, `maintainers` produces a list containing the
# usernames of the package's maintainers.  Likewise, the licenses method
# yields a list of the names of the licenses for a given package.

# A resource method is just a class method on a handler class.
# When invoked, it is passed an instance of the model associated with
# the class.  For PackageInfoHandler, that is Package.  It returns the value
# of a field, for presentation to the client via the API.

    @classmethod
    def repository(cls, pkg):
        """Return the name of the repository containing the package."""
        return pkg.repository.name

    @classmethod
    def maintainers(cls, pkg):
        """Return the usernames of the package's maintainers."""
        return [x.username for x in pkg.maintainers.all()]

    @classmethod
    def licenses(cls, pkg):
        return [x.name for x in pkg.licenses.all()]

    @classmethod
    def architectures(cls, pkg):
        return [x.name for x in pkg.architectures.all()]

    @classmethod
    def depends(cls, pkg):
        return [x.name for x in pkg.depends.all()]

    @classmethod
    def make_depends(cls, pkg):
        return [x.name for x in pkg.make_depends.all()]

    @classmethod
    def provides(cls, pkg):
        return [x.name for x in pkg.provides.all()]

    @classmethod
    def conflicts(cls, pkg):
        return [x.name for x in pkg.conflicts.all()]

    @classmethod
    def replaces(cls, pkg):
        return [x.name for x in pkg.replaces.all()]

    @classmethod
    def groups(cls, pkg):
        return [x.name for x in pkg.groups.all()]

    @classmethod
    def sources(cls, pkg):
        """Return a list of the URLs of the source files for this package."""
        return [x.get_absolute_url()
                for x in pkg.packagefile_set.all()]

    @classmethod
    def md5(cls, pkg):
        """Return the MD5 digests of the package's source files."""
        return get_hashes(pkg, u'md5')

    @classmethod
    def sha1(cls, pkg):
        """Return the MD5 digests of the package's source files."""
        return get_hashes(pkg, u'sha1')

    @classmethod
    def added(cls, pkg):
        """Return the time at which this package was added, represented
        as the number of epoch seconds."""
        return int(time.mktime(pkg.added.timetuple()))

    @classmethod
    def updated(cls, pkg):
        """Return the time at which this package was last updated, represented
        as the number of epoch seconds."""
        return int(time.mktime(pkg.updated.timetuple()))

    @classmethod
    def tarball(cls, pkg):
        """Return the URL of the tarball that contains this package's PKGBUILD."""
        return pkg.tarball.url

    @classmethod
    def permalink(cls, pkg):
        """Return the URL for the AUR package page."""
        domain = Site.objects.get_current().domain
        base = 'http://%s' % (domain,)
        return urlparse.urljoin(base, pkg.get_absolute_url())

    @classmethod
    def comments(cls, pkg):
        """Return the number of comments for the given package."""
        return pkg.comment_set.count()

    def read(self, request, object_id=None):
        """Handle GET requests.  If object_id is not None,
        then return the corresponding package object from the database.
        Otherwise, look at the query from the request, and return
        all matching packages.  Right now, this just returns all packages
        in the database."""
        if not object_id:
            # Handle /api/packages.
            return Package.objects.all()
        else:
            try:
                return Package.objects.get(name=object_id)
            except Package.DoesNotExist:
                # We can't use get_object_or_404!
                resp = rc.NOT_FOUND
                resp.write('\nPackage %s was not found.' % (object_id,))
                # Ideally, we should send an object in the desired format:
                # E.G., {"error" : "Package %s not found"} for JSON.
                return resp

class AnonymousPackageInfoHandler(BasePackageInfoHandler, AnonymousBaseHandler):
    allowed_methods = ('GET',)
    model = Package
    fields = pkg_info_fields

class PackageInfoHandler(BasePackageInfoHandler):
    anonymous = AnonymousPackageInfoHandler
    allowed_methods = ('GET', 'POST', 'PUT', 'DELETE')
    model = Package
    fields = pkg_info_fields

    # TODO: Implement the following HTTP methods

    def create(self, pkg, object_id=None):
        """Handle POST requests."""
        return rc.NOT_IMPLEMENTED

    def update(self, pkg, object_id=None):
        """Handle PUT requests."""
        return rc.NOT_IMPLEMENTED

    def delete(self, pkg, object_id=None):
        """Handle DELETE requests."""
        return rc.NOT_IMPLEMENTED

