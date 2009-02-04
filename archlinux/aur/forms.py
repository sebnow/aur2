import tarfile
import os
from parched import PKGBUILD

from django import forms
from django.core.files import File

from aur.models import *
from pkgbuild import PKGBUILDValidator


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
        # Get the PKGBUILD out of the tarball if one was uploaded
        # try:
        #     tarfileobj = tarfile.open(fileobj=cleaned_file)
        #     found = False
        #     for name in tarfileobj.getnames():
        #         if name.find("PKGBUILD") >= 0:
        #             found = True
        #             fileobj = tarfileobj.extractfile(name)
        #     if not found:
        #         tarfileobj.close()
        #         raise forms.ValidationError("PKGBUILD could not be found in tarball")
        # except tarfile.ReadError:
        #     fileobj = cleaned_file
        fileobj = cleaned_file
        package = PKGBUILD(fileobj=fileobj)
        validator = PKGBUILDValidator(package)
        validator.validate()
        errors.extend(validator.errors)
        errors.extend(validator.warnings)
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

    #@transaction.commit_manually
    def save(self, user):
        if not self.is_valid():
            return
        import hashlib
        cleaned_file = self.cleaned_data['package']
        # PKGBUILD's file-like object
        fileobj = None
        tarfileobj = None
        # try:
        #     tarfileobj = tarfile.open(fileobj=cleaned_file)
        #     for name in tarfileobj.getnames():
        #         if name.find("PKGBUILD") >= 0:
        #             fileobj = tarfileobj.extractfile(name)
        # except tarfile.ReadError:
        #     fileobj = cleaned_file
        fileobj = cleaned_file
        pkgbuild = PKGBUILD(fileobj=fileobj)
        updating = False
        try:
            package = Package.objects.get(name=pkgbuild.name)
            updating = True
        except Package.DoesNotExist:
            package = Package(name=pkgbuild.name)
        self._save_metadata(package, pkgbuild, updating)
        # Remove all sources. It's easier and cleaner this way.
        if updating:
            PackageFile.objects.filter(package=package.name).delete()
            package.tarball.delete()
        # Hash and save PKGBUILD
        source = PackageFile(package=package)
        source.filename.save('%(name)s/sources/PKGBUILD', fileobj)
        source.save()
        fileobj.seek(0)
        digest = hashlib.md5("\n".join(fileobj.readlines())).hexdigest()
        fileobj.seek(0)
        PackageHash(hash=digest, file=source, type='md5').save()
        if tarfileobj is None:
            tarfileobj = self._tarfile_from_pkgbuild(fileobj, package.name)
        else:
            self._save_files(package, pkgbuild, tarfileobj)
        transaction.commit()

    def _save_metadata(self, package, pkgbuild, updating):
        package.version = pkgbuild.version
        package.release = pkgbuild.release
        package.description = pkgbuild.description
        package.url = pkgbuild.url
        repository = self.cleaned_data['repository']
        package.repository=Repository.objects.get(name__iexact=repository)
        # Save the package so we can reference it
        package.save()
        # Implicitely add uploader as the maintainer
        if not updating:
            package.maintainers.add(user)
        else:
            # TODO: Check if user can upload/overwrite the package
            pass
        # Check for, and add dependencies
        for dependency in pkgbuild.depends:
            try:
                package.depends.add(Package.objects.get(name=dependency))
            except Package.DoesNotExist:
                # Ignore external dependencies
                pass
        # Add provides
        for provision in pkgbuild.provides:
            p, created = Provision.objects.get_or_create(name=provision)
            package.provides.add(p)
        # Add licenses
        for license in pkgbuild.licenses:
            l, created = License.objects.get_or_create(name=license)
            package.licenses.add(l)
        # Add architectures
        for arch in pkgbuild.architectures:
            a = Architecture.objects.get(name=arch)
            package.architectures.add(a)

    def _save_files(self, package, pkgbuild, tarfileobj):
        # Save tarball
        # TODO: Tar the saved sources instead of using the uploaded one, for
        # security
        path = os.path.join('%(name)s', package.name + 'tar.gz')
        package.tarball.save(path, File(open(tarfileobj.name, "rb")))
        # Save source files
        names = tarfileobj.getnames()
        for index, source_filename in pkgbuild.sources:
            source = PackageFile(package=package)
            # If it's a local file, save to disk, otherwise record as url
            if tarfileobj:
                found = False
                fp = None
                for name in names:
                    if name.find(source_filename) >= 0:
                        fp = tarfileobj.extractfile(name)
                        found = True
                        break
                if found:
                    source.filename.save('%(name)s/sources/' + source_filename, fp)
                    fp.close()
                else:
                    source.url = source_filename
            else:
                # TODO: Check that it _is_ a url, otherwise report an error
                # that files are missing
                source.url = source_filename
            source.save()
            # Check for, and save, any hashes this file may have
            for hash_type in pkgbuild.checksums:
                if pkgbuild.checksums[hash_type]:
                    PackageHash(hash=pkgbuild.checksums[hash_type][index],
                            file=source, type=hash_type).save()
        # Save install files
        source = PackageFile(package=package)
        if pkgbuild.install:
            names = tarfileobj.getnames()
            path = os.path.join(package.name, pkgbuild.install)
            install = None
            if path in names:
                install = tarfileobj.extractfile(path)
            else:
                install = tarfileobj.extractfile(pkgbuild.install)
            source.filename.save('%(name)s/sources/' + pkgbuild.install, install)
            instal.close()
            source.save()
        transaction.commit()

    def _tarfile_from_pkgbuild(self, fileobj, name):
        """Create a tarball in a temporary directory, containing *fileobj*.
        
        .. note::
        
            The returned :class:`TarFile` object is open for reading.
        """
        import tempfile
        tarball_name = name + '.tar.gz'
        tarball_path = os.path.join(tempfile.mkdtemp(), tarball_name)
        # TODO: Is there a way to add the fileobj to the tarfile from memory?
        pkgbuild_path = os.path.join(tempfile.mkdtemp(), "PKGBUILD")
        pkgbuild = open(pkgbuild_path, "w")
        pkgbuild.writelines(fileobj.readlines())
        pkgbuild.close()
        tarfileobj = tarfile.open(str(tarball_path), "w|gz")
        tarfileobj.add(pkgbuild_path, os.path.join(name, "PKGBUILD"))
        tarfileobj.close()
        os.remove(pkgbuild_path)
        os.rmdir(os.path.dirname(pkgbuild_path))
        tarfileobj = tarfile.open(str(tarball_path), "r")
        return tarfileobj

