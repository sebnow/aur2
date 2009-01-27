from django import forms

from archlinux.aur.models import *
import archlinux.aur.Package as PKGBUILD

import os
import sys

class PackageSearchForm(forms.Form):
    # Borrowed from AUR2-BR
    def __init__(self, *args, **kwargs):
        super(PackageSearchForm, self).__init__(*args, **kwargs)
        category_choices = [('all', 'All')]
        category_choices += [(category.name.lower(), category.name) for category in Category.objects.all()]
        repository_choices = [('all', 'All')]
        repository_choices += [(repository.name.lower(), repository.name) for repository in Repository.objects.all()]
        self.fields['category'].choices = category_choices
        self.fields['repository'].choices = repository_choices

    repository = forms.ChoiceField(initial='all', choices=())
    category = forms.ChoiceField(initial='all', choices=())
    query = forms.CharField(max_length=30, label="Keywords", required=False)
    searchby = forms.ChoiceField(initial='name', label="Search By",choices=(
        ('name', 'Package Name'),
        ('maintainer', 'Maintainer'),
    ))
    lastupdate = forms.DateTimeField(label="Last Update", required=False)
    limit = forms.ChoiceField(initial='25', choices=(
        (25, 25),
        (50, 50),
        (75, 75),
        (100, 100),
        (150, 150),
    ))

    def get_or_default(self, key):
        if not self.is_bound:
            return self.fields[key].initial
        return self.cleaned_data.get(key, self.fields[key].initial)

    def search(self):
        if self.is_bound and not self.is_valid():
            return None
        repository = self.get_or_default('repository')
        lastupdate = self.get_or_default('lastupdate')
        category = self.get_or_default('category')
        query = self.get_or_default('query')

        # Find the packages by searching description and package name or maintainer
        if query:
            if self.get_or_default('searchby') == 'maintainer':
                results = Package.objects.filter(maintainers__username__icontains=query)
            else:
                results = Package.objects.filter(name__icontains=query)
                results |= Package.objects.filter(description__icontains=query)
        else:
            results = Package.objects.all()
        # Restrict results
        if repository != 'all':
            results = results.filter(repository__name__iexact=repository)
        if category != 'all':
            results = results.filter(category__name__exact=category)
        if lastupdate:
            results = results.filter(updated__gte=lastupdate)
        return results


class PackageField(forms.FileField):
    widget = forms.widgets.FileInput
    def __init__(self, *args, **kwargs):
        super(forms.FileField, self).__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        import tempfile
        import tarfile
        try:
            file = super(PackageField, self).clean(data, initial)
        except:
            raise
        errors = list()
        # Save the uploaded file to disk
        directory = tempfile.mkdtemp()
        filename = os.path.join(directory, file.name)
        fp = open(filename, "wb")
        for chunk in file.chunks():
            fp.write(chunk)
        fp.close()

        # Try to parse the PKGBUILD
        try:
            pkg = PKGBUILD.Package(filename)
        except:
            raise forms.ValidationError(sys.exc_info()[1])
        # Add path of the tarball/PKGBUILD so we can reference in other places
        pkg['filename'] = filename
        # Validate PKGBUILD
        pkg.validate()
        if not pkg.is_valid() or pkg.has_warnings():
            errors.extend(pkg.get_errors())
            errors.extend(pkg.get_warnings())
        # Check if we have everything we need
        for arch in pkg['arch']:
            try:
                Architecture.objects.get(name=arch)
            except Architecture.DoesNotExist:
                errors.append('architecture %s does not exist' % arch)
        if pkg['install']:
            try:
                tar = tarfile.open(filename)
            except tarfile.ReadError:
                errors.append('install files are missing')
            else:
                files = tar.getnames()
                for file in pkg['install']:
                    filepath = os.path.join(pkg['name'], file)
                    if not filepath in files:
                        errors.append('install file "%s" is missing' % file)
                del files
        # Report errors or return the validated package
        if errors:
            raise forms.ValidationError(errors)
        else:
            return pkg


class PackageSubmitForm(forms.Form):
    category = forms.ChoiceField(choices=())
    package = PackageField(label="PKGBUILD")

    # Borrowed from AUR2-BR
    def __init__(self, *args, **kwargs):
        super(PackageSubmitForm, self).__init__(*args, **kwargs)
        category_choices = [(category.name.lower(), category.name) for category in Category.objects.all()]
        self.fields['category'].choices = category_choices

    @transaction.commit_manually
    def save(self, user):
        import hashlib
        import tarfile
        pkg = self.cleaned_data['package']
        tmpdir = os.path.dirname(pkg['filename'])
        updating = False
        creating = False
        try:
            package = Package.objects.get(name=pkg['name'])
        except Package.DoesNotExist:
            package = Package(name=pkg['name'])
            creating = True
        else:
            updating = True
        package.version=pkg['version']
        package.release=pkg['release']
        package.description=pkg['description']
        package.url=pkg['url']
        package.repository=Repository.objects.get(name="Unsupported")
        package.category=Category.objects.get(name=self.cleaned_data['category'])
        # Save the package so we can reference it
        package.save()
        if creating:
            package.maintainers.add(user)
        else:
            # TODO: Check if user can upload/overwrite the package
            pass
        # Check for, and add dependencies
        for dependency in pkg['depends']:
            # This would be nice, but we don't have access to the official
            # repositories
            try:
                dep = Package.objects.get(name=dependency)
            except Package.DoesNotExist:
                # Fail silently
                pass
            else:
                package.depends.add(dep)
        # Add provides
        for provision in pkg['provides']:
            object, created = Provision.objects.get_or_create(name=provision)
            package.provides.add(object)
        # Add licenses
        for license in pkg['licenses']:
            object, created = License.objects.get_or_create(name=license)
            package.licenses.add(object)
        # Add architectures
        for arch in pkg['arch']:
            object = Architecture.objects.get(name=arch)
            package.architectures.add(object)
        # Check if the uploaded file is a tar file or just a PKGBUILD
        try:
            tar = tarfile.open(pkg['filename'], "r")
        except tarfile.ReadError:
            # It's not a tar file, so if must be a PKGBUILD since it validated
            is_tarfile = False
            pkgbuild = pkg['filename']
        else:
            is_tarfile = True
            tmpdir_sources = os.path.join(tmpdir, 'sources')
            tar.extractall(tmpdir_sources)
            pkgbuild = os.path.join(tmpdir_sources, pkg['name'], 'PKGBUILD')
        # Remove all sources. It's easier and cleaner this way.
        if updating:
            PackageFile.objects.filter(package=pkg['name']).delete()
            package.delete_tarball()
        # Hash and save PKGBUILD
        fp = open(pkgbuild, "r")
        pkgbuild_contents = ''.join(fp.readlines())
        fp.close()
        source = PackageFile(package=package)
        source.save_filename_file('%s/sources/PKGBUILD' % pkg['name'],
                pkgbuild_contents)
        source.save()
        md5hash = hashlib.md5(pkgbuild_contents)
        hash = PackageHash(hash=md5hash.hexdigest(), file=source, type='md5')
        hash.save()
        del pkgbuild_contents
        # Save tarball
        # TODO: Tar the saved sources instead of using the uploaded one, for
        # security
        if not is_tarfile:
            # We only have the PKGBUILD, so lets make a tarball
            tar = tarfile.open(os.path.join(tmpdir, '%s.tar.gz' % pkg['name']),
                    "w|gz")
            tar.add(pkg['filename'], '%s/PKGBUILD' % pkg['name'])
            tar.close()
            pkg['filename'] = os.path.join(tmpdir, '%s.tar.gz' % pkg['name'])
        fp = open(pkg['filename'], "rb")
        package.save_tarball_file('%s/%s' % (pkg['name'],
            os.path.basename(pkg['filename'])), ''.join(fp.readlines()))
        fp.close()
        # Save source files
        for index in range(len(pkg['source'])):
            source_filename = pkg['source'][index]
            source = PackageFile(package=package)
            # If it's a local file, save to disk, otherwise record as url
            if is_tarfile and os.path.exists(os.path.join(tmpdir_sources,
               package.name, source_filename)):
                    fp = open(os.path.join(tmpdir_sources, pkg['name'],
                        source_filename), "r")
                    source.save_filename_file('%s/sources/%s' % (pkg['name'],
                        source_filename), ''.join(fp.readlines()))
                    fp.close()
            else:
                # TODO: Check that it _is_ a url, otherwise report an error
                # that files are missing
                source.url = source_filename
            source.save()
            # Check for, and save, any hashes this file may have
            for hash_type in ('md5', 'sha1', 'sha256', 'sha384', 'sha512'):
                if pkg[hash_type + 'sums']:
                    PackageHash(hash=pkg[hash_type + 'sums'][index],
                            file=source, type=hash_type).save()
        # Save install files
        for file in pkg['install']:
            source = PackageFile(package=package)
            source_path = os.path.join(tmpdir_sources, pkg['name'], file)
            fp = open(source_path, "r")
            source.save_filename_file('%s/install/%s' % (pkg['name'], file),
                    ''.join(fp.readlines()))
            fp.close()
            source.save()
        transaction.commit()
        # Remove temporary files
        for root, dirs, files in os.walk(tmpdir, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        os.rmdir(tmpdir)
