import re
import hashlib
import tempfile
from parched import PKGBUILD

from django.db import transaction

from archlinux.aur.models import Package, PackageHash, PackageFile

class PKGBUILDValidator(object):
    def __init__(self, package):
        self._package = package
        self._is_valid = None
        self._errors = None
        self._warnings = None
        self._required_fields = (
            'name',
            'description',
            'version',
            'release',
            'licenses',
            'architectures',
        )
    @property
    def is_valid(self):
        """
        Return True is the form has no errors. Otherwise, False.
        """
        return bool(self.errors)

    @property
    def errors(self):
        """
        Return a list of errors after validation.
        """
        if self._errors is None:
            self.validate()
        return self._errors

    @property
    def warnings(self):
        """
        Return a list of warnings after validation.
        """
        if self._warnings is None:
            self.validate()
        return self._warnings


    def validate(self):
        """
        Validate PKGBUILD for missing or invalid fields
        """
        self._errors = []
        self._warnings = []
        # Search for missing fields
        for field in self._required_fields:
            if not getattr(self._package, field):
                self._errors.append(field + ' field is required')
        # Validate name
        if not re.match("^[\w\d_-]+$", self._package.name):
            self._errors.append('name must be alphanumeric')
        # Furthur validate name to be more specific with error messages
        elif not re.match("[a-z\d_-]+", self._package.name):
            self._warnings.append('name should be in lower case')
        if self._package.version.find('-') >= 0:
            self._errors.append('version is not allowed to contain hyphens')
        # Description isn't supposed to be longer than 80 characters
        if self._package.description and len(self._package.description) > 80:
            self._warnings.append("description should't exceed 80 characters")
        # Make sure the number of sources and checksums is the same
        found_sums = False
        for algorithm in self._package.checksums:
            checksum = self._package.checksums[algorithm]
            if checksum:
                found_sums = True
                if len(checksum) != len(self._package.sources):
                    self._errors.append('amount of %ssums '
                        'and sources does not match' % algorithm
                    )
        if self._package.sources and not found_sums:
            self._errors.append('sources exist without checksums')


class PackageUploader(object):
    def __init__(self, tarfileobj, repository):
        self.tarfileobj = tarfileobj
        self.pkgbuild = None
        self.fileobj = None
        self.package = None
        self.repository = repository
        self.updating = False
        for name in tarfileobj.getnames():
            if name.find("PKGBUILD") >= 0:
                self.fileobj = tarfile.extractfile(name)
                self.pkgbuild = PKGBUILD(self.fileobj)
                break;
        if self.pkgbuild is None:
            raise ValueError("PKGBUILD not found in tarfile")
        if not self.pkgbuild.is_valid:
            raise ValueError("PKGBUILD has to be valid")

    @transaction.commit_manually
    def save(self):
        try:
            self.package = Package.objects.get(name=self.pkgbuild.name)
            self.updating = True
        except Package.DoesNotExist:
            self.package = Package(name=self.pkgbuild.name)
        self._save_metadata()
        if self.updating:
            PackageFile.objects.filter(package=self.pkgbuild.name).delete()
            self.package.tarball.delete()
        self._save_tarball()
        self._save_pkgbuild()
        self._save_sources()
        self._save_install()
        self.package.save()
        transaction.commit()

    def _save_metadata(self):
        self.package.version = self.pkgbuild.version
        self.package.release = self.pkgbuild.release
        self.package.description = self.pkgbuild.description
        self.package.url = self.pkgbuild.url
        self.package.repository = Repository.objects.get(
            name__iexact=self.repository)
        # Save the package so we can reference it
        self.package.save()
        # Implicitely add uploader as the maintainer
        #if not updating:
        #    self.package.maintainers.add(user)
        #else:
        #    # TODO: Check if user can upload/overwrite the package
        #    pass
        # Check for, and add dependencies
        for dependency in self.pkgbuild.depends:
            try:
                self.package.depends.add(Package.objects.get(name=dependency))
            except Package.DoesNotExist:
                # Ignore external dependencies
                pass
        # Add provides
        for provision in self.pkgbuild.provides:
            p, created = Provision.objects.get_or_create(name=provision)
            self.package.provides.add(p)
        # Add licenses
        for license in self.pkgbuild.licenses:
            l, created = License.objects.get_or_create(name=license)
            self.package.licenses.add(l)
        # Add architectures
        for arch in self.pkgbuild.architectures:
            a = Architecture.objects.get(name=arch)
            self.package.architectures.add(a)

    def _save_tarball(self):
        # Django's storage API doesn't like tarfile objects, so it's
        # opened as a file
        path = os.path.join('%(name)s', self.pkgbuild.name + 'tar.gz')
        fp = File(open(self.tarfileobj.name, "rb"))
        package.tarball.save(path, fp)
        fp.close()
    
    def _save_pkgbuild(self):
        source = PackageFile(package=self.package)
        source.filename.save('%(name)s/sources/PKGBUILD', self.fileobj)
        source.save()
        digest = self._hash_of_file(self.fileobj)
        PackageHash(hash=digest, file=source, type='md5').save()

    def _save_sources(self):
        for index, filename in self.pkgbuild.sources:
            source = PackageFile(package=self.package)
            # If it's a local file, save to disk, otherwise record as url
            fp = None
            for name in self.tarfileobj.getnames():
                if name.find(filename) >= 0:
                    fp = tarfileobj.extractfile(name)
                    break
            if not fp is None:
                source.filename.save('%(name)s/sources/' + filename, fp)
                fp.close()
            else:
                # TODO: Check that it _is_ a url, otherwise report an error
                # that files are missing
                source.url = filename
            source.save()
            # Check for, and save, any hashes this file may have
            for hash_type in self.pkgbuild.checksums:
                if self.pkgbuild.checksums[hash_type]:
                    PackageHash(hash=self.pkgbuild.checksums[hash_type][index],
                            file=source, type=hash_type).save()

    def _save_install(self):
        if pkgbuild.install:
            names = tarfileobj.getnames()
            path = os.path.join(self.pkgbuild.name, self.pkgbuild.install)
            install = None
            if path in names:
                install = tarfileobj.extractfile(path)
            else:
                install = tarfileobj.extractfile(pkgbuild.install)
            self.package.install.save('%(name)s/' + pkgbuild.install, install)
            install.close()

    def _hash_of_file(self, fileobj):
        if hasattr(fileobj):
            fileobj.seek(0)
        digest = hashlib.md5("\n".join(fileobj.readlines())).hexdigest()
        if hasattr(fileobj):
            fileobj.seek(0)
        return digest

