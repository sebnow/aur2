import tarfile
import os

from django import forms
from django.core.files import File

from aur.models import Package, Repository, Architecture
from pkgbuild import ValidPKGBUILD, PackageUploader

class PackageSearchForm(forms.Form):
    # Borrowed from AUR2-BR
    def __init__(self, *args, **kwargs):
        super(PackageSearchForm, self).__init__(*args, **kwargs)
        repository_choices = [('all', 'All')]
        repository_choices += [(repository.name.lower(), repository.name) for repository in Repository.objects.all()]
        self.fields['repository'].choices = repository_choices

    repository = forms.ChoiceField(initial='all', choices=(), required=False)
    query = forms.CharField(max_length=30, label="Keywords", required=False)
    searchby = forms.ChoiceField(
        initial='name',
        required=False,
        label="Search By",choices=(
            ('name', 'Package Name'),
            ('maintainer', 'Maintainer'),
        )
    )
    lastupdate = forms.DateTimeField(label="Last Update", required=False)
    limit = forms.ChoiceField(initial='25', required=False, choices=(
        (25, 25),
        (50, 50),
        (75, 75),
        (100, 100),
        (150, 150),
    ))

    def get_or_default(self, key):
        if not self.is_bound:
            return self.fields[key].initial
        return self.cleaned_data.get(key) or self.fields[key].initial

    def search(self):
        if self.is_bound and not self.is_valid():
            return None
        repository = self.get_or_default('repository')
        lastupdate = self.get_or_default('lastupdate')
        query = self.get_or_default('query')

        # Find the packages by searching description and package name or maintainer
        if query:
            if self.get_or_default('searchby') == 'maintainer':
                results = Package.objects.filter(maintainers__username__icontains=query)
            else:
                results = Package.objects.filter(name__icontains=query)
                results |= Package.objects.filter(description__icontains=query)
                # Split query to search for each word as a tag
                for keyword in query.split():
                    results |= Package.objects.filter(tags__exact=keyword)
        else:
            results = Package.objects.all()
        # Restrict results
        if repository != 'all':
            results = results.filter(repository__name__iexact=repository)
        if lastupdate:
            results = results.filter(updated__gte=lastupdate)
        return results


class PackageField(forms.FileField):
    widget = forms.widgets.FileInput
    def __init__(self, *args, **kwargs):
        super(PackageField, self).__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        tarfileobj = None
        fileobj = None
        cleaned_file = super(PackageField, self).clean(data, initial)
        errors = []
        # If cleaned_file is a tarfile, extract the PKGBUILD, otherwise
        # assume cleaned_file is the PKGBUILD
        try:
            tarfileobj = tarfile.open(fileobj=cleaned_file)
            found = False
            for name in tarfileobj.getnames():
                if name.find("PKGBUILD") >= 0:
                    found = True
                    fileobj = tarfileobj.extractfile(name)
                    break
            if not found:
                tarfileobj.close()
                raise forms.ValidationError("PKGBUILD could not be found in the tarball")
            tarfileobj.close()
            del tarfileobj
        except tarfile.ReadError:
            fileobj = cleaned_file
        if fileobj is None:
            raise forms.ValidationError("PKGBUILD could not be found in tarball")
        package = ValidPKGBUILD(fileobj=fileobj)
        package.validate()
        errors.extend(package.errors)
        errors.extend(package.warnings)
        # Check if we have everything we need
        for arch in package.architectures:
            try:
                Architecture.objects.get(name=arch)
            except Architecture.DoesNotExist:
                errors.append('architecture {0} does not exist'.format(arch))
        if package.install:
            if tarfileobj:
                files = tar.getnames()
                filepath = os.path.join(package.name, file)
                if not package.install in files and not filepath in files:
                        errors.append('install scriptlet is missing')
            else:
                errors.append('install scriptlet is missing')
        if tarfileobj:
            fileobj.close()
        if errors:
            raise forms.ValidationError(errors)
        return cleaned_file


class PackageSubmitForm(forms.Form):
    repository = forms.ChoiceField(choices=())
    package = PackageField(label="PKGBUILD")

    # Borrowed from AUR2-BR
    def __init__(self, *args, **kwargs):
        super(PackageSubmitForm, self).__init__(*args, **kwargs)
        repo_choices = [(repo.name.lower(), repo.name) for repo in Repository.objects.all()]
        self.fields['repository'].choices = repo_choices

    def save(self, user):
        if not self.is_valid():
            return
        import hashlib
        fileobj = self.cleaned_data['package']
        tarfileobj = None
        try:
            tarfileobj = tarfile.open(fileobj=fileobj)
        except tarfile.ReadError:
            tarfileobj = _tarfile_from_pkgbuild(fileobj)
        package = PackageUploader(tarfileobj, self.cleaned_data['repository'])
        package.save()
        tarfileobj.close()


def _tarfile_from_pkgbuild(fileobj):
    """Create a tarball in a temporary directory, containing *fileobj*.

    .. note::

        The returned :class:`TarFile` object is open for reading.
    """
    import tempfile
    tarball_path = os.path.join(tempfile.mkdtemp(), 'tmp.tar.gz')
    # TODO: Is there a way to add the fileobj to the tarfile from memory?
    pkgbuild_path = os.path.join(tempfile.mkdtemp(), "PKGBUILD")
    pkgbuild = open(pkgbuild_path, "w")
    if hasattr(fileobj):
        fileobj.seek(0)
    pkgbuild.writelines(fileobj.readlines())
    if hasattr(fileobj):
        fileobj.seek(0)
    pkgbuild.close()
    tarfileobj = tarfile.open(str(tarball_path), "w|gz")
    tarfileobj.add(pkgbuild_path, os.path.join(name, "PKGBUILD"))
    tarfileobj.close()
    os.remove(pkgbuild_path)
    os.rmdir(os.path.dirname(pkgbuild_path))
    tarfileobj = tarfile.open(str(tarball_path), "r")
    return tarfileobj
