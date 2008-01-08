#!/usr/bin/env python
import os
import subprocess
import re
import tarfile
import tempfile
from UserDict import UserDict

class InvalidPackage(Exception):
    pass


class Package(UserDict):
    """Representation of an Archlinux package"""
    def __init__(self, file):
        UserDict.__init__(self)
        self._required_fields = (
            'name', 'description', 'version', 'release',
            'licenses', 'arch',
        )
        self._validated = False
        self._is_valid = False
        self._errors = []
        self._warnings = []

        self.load(file)

    def load(self, file):
        """Parse a PKGBUILD (can be within a tar file) and import the variables"""
        if not os.path.exists(file):
            raise Exception("file does not exist")
        script_dir = os.path.dirname(__file__)
        if not script_dir:
            script_dir = os.path.abspath(script_dir)
        is_temporary = False

        # Check if it's a tarballed PKGBUILD and extract it
        try:
            tar = tarfile.open(file, "r")
        except:
            if os.path.basename(file) != "PKGBUILD":
                raise
        else:
            to_extract = None
            for member in tar.getnames():
                if member.find("PKGBUILD") >= 0:
                    to_extract = member
                    break
            if not to_extract:
                raise InvalidPackage('tar file does not contain a PKGBUILD')
            # Create a temporary directory and extract to it
            directory = tempfile.mkdtemp()
            tar.extract(to_extract, directory)
            file = os.path.join(directory, to_extract)
            is_temporary = True

        # Find the current directory and filename
        working_dir = os.path.dirname(file)
        if working_dir == '':
            working_dir = None
        filename = os.path.basename(file)

        # Let's parse the PKGBUILD
        process = subprocess.Popen([
            os.path.join(script_dir, 'parsepkgbuild.sh'), filename],
            stdout=subprocess.PIPE, cwd=working_dir)
        process.wait()

        # "Import" variables into local namespace
        for expression in process.stdout.readlines():
            exec 'temp = dict(' + expression.rstrip() + ')'
            self.update(temp)

        # Remove the temporary file since we don't need it
        if is_temporary:
            os.remove(file)
            #os.removedirs(directory)

    def validate(self):
        """Validate PKGBUILD for missing or invalid fields"""
        # Search for missing fields
        for field in self._required_fields:
            if not self[field]:
                self._errors.append('%s field is required' % field)
        if not re.compile("^[\w\d_-]+$").match(self['name']):
            self._errors.append('package name must be alphanumeric')
        elif not re.compile("[a-z\d_-]+").match(self['name']):
            self._warnings.append('package name should be in lower case')
        if self['version'].find('-') >= 0:
            self._errors.append('version field is not allowed to contain hyphens')
        if str(self['release']).find('-') >= 0:
            self._errors.append('release field is not allowed to contain hyphens')
        # Description isn't supposed to be longer than 80 characters
        if self['description'] and len(self['description']) > 80:
            self._warnings.append('description should not exceed 80 characters')
        # Make sure the number of sources and checksums is the same
        found_sums = False
        for checksum in ('md5sums', 'sha1sums', 'sha256sums', 'sha384sums',
                         'sha512sums'):
            if self[checksum]:
                found_sums = True
                if len(self[checksum]) != len(self['source']):
                    self._errors.append('amount of %s and sources does not match'
                            % checksum)
        if self['source'] and not found_sums:
            self._errors.append('sources exist without checksums')
        # Set some variables to quickly determine whether the package is valid
        self._validated = True
        if not self.has_errors():
            self._is_valid = True

    def is_valid(self):
        """If Package wasn't validated already, validate and report whether
        package is valid"""
        if not self._validated:
            self.validate()
        return self._is_valid

    def has_errors(self):
        """Determine whether package has any errors"""
        return len(self._errors) > 0

    def has_warnings(self):
        """Determin whether the package has any warnings"""
        return len(self._warnings) > 0

    def get_errors(self):
        """Retrieve a list of errors"""
        return self._errors

    def get_warnings(self):
        """Retrieve a list of warnings"""
        return self._warnings
