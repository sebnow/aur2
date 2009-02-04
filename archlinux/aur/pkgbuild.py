import re

from parched import PKGBUILD

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

