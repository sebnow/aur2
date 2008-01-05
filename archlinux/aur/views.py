from re import sub
import os
import sys

from django.shortcuts import render_to_response, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect
from BetterPaginator import BetterPaginator
from django import newforms as forms # This will change to forms in 0.68 or 1.0
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.db import transaction

from archlinux.aur.models import *
import archlinux.aur.Package as PKGBUILD

def search(request, query = ''):
    if request.method == 'GET' and request.GET.has_key('query'):
        form = PackageSearchForm(request.GET)
        # If there are any errors in the forum, render the template and exit
        if not form.is_valid():
            return render_to_response('aur/search.html', {
                'form': form,
                'user': request.user
            })
    else:
        form = PackageSearchForm()
    # Execute the search
    results = form.search()
    # If we only got one hit, just go to the package's detail page
    if results.count() == 1:
        return HttpResponseRedirect(reverse('aur-package_detail',
            args=[results[0].name,]))
    # Replace the current page with the new one if it's already in GET
    if request.GET.has_key('page'):
        link_template = sub(r'page=\d+', 'page=%d', request.get_full_path())
    else:
        link_template = request.get_full_path() + '&page=%d'
    # Initialise the pagination
    paginator = BetterPaginator(results, int(form.get_or_default('limit')), link_template)
    paginator.set_page(int(request.GET.get('page', '1')))

    return render_to_response('aur/search.html', {
        'form': form,
        'packages': paginator.get_page(),
        'pager': paginator,
        'user': request.user,
    })

# TODO: Implement transactions
@login_required
def submit(request):
    if request.method == 'POST':
        form = PackageSubmitForm(request.POST, request.FILES)
        if not form.is_valid():
            return render_to_response('aur/submit.html', {
                'user': request.user, 'form': form})
        import tempfile
        directory = tempfile.mkdtemp()
        filename = os.path.join(directory, form.cleaned_data['file'].filename)
        # Save the uploaded file to disk
        fp = open(filename, "wb")
        fp.write(form.cleaned_data['file'].content)
        fp.close()

        try:
            pkg = PKGBUILD.Package(filename)
        except:
            # TODO: Add error to form
            return render_to_response('aur/submit.html', {
                'user': request.user, 'form': form, 'errors': sys.exc_info()[1]})
        pkg.validate()
        if not pkg.is_valid() or pkg.has_warnings():
            return render_to_response('aur/submit.html', {
                'user': request.user, 'form': form, 'errors': pkg.get_errors(),
                'warnings': pkg.get_warnings()})

        # Check if we are updating an existing package or creating one

        package = Package(name=pkg['name'], version=pkg['version'],
                release=pkg['release'], description=pkg['description'],
                url=pkg['url'])

        package.repository=Repository.objects.get(name__exact="Unsupported")
        package.category=Category.objects.get(name__iexact=form.cleaned_data['category'])

        # Check for, and add dependencies
        for dependency in pkg['depends']:
            # This would be nice, but we don't have access to the official
            # repositories
            #if Package.objects.filter(name=dependency).count() == 0:
                # TODO: Display an error
                #return render_to_response("aur/submit.html")
            try:
                dep = Package.objects.get(name__exact=dependency)
            except Package.DoesNotExist:
                # Fail silently
                pass
            else:
                package.depends.add(dep)

        # Save the package so we can reference it
        package.save()
        package.maintainers.add(request.user)
        for license in pkg['licenses']:
            object, created = License.objects.get_or_create(name=license)
            package.licenses.add(object)
        for arch in pkg['arch']:
            try:
                object = Architecture.objects.get(name=arch)
            except Architecture.DoesNotExist:
                # TODO: Add an error
                return render_to_response('aur/submit.html', {
                    'user': request.user,
                    'form': form,
                    'errors': ['architecture %s does not exist' % arch,],
                })
            else:
                package.architectures.add(object)

        for index in range(len(pkg['source'])):
            source = PackageFile(package=package,
                    filename=pkg['source'][index])
            source.save()
            # Check for any hashes this file may have
            if pkg['md5sums']:
                hash = PackageHash(hash=pkg['md5sums'][index], file=source,
                        type='md5sum')
                hash.save()
            if pkg['sha1sums']:
                hash = PackageHash(hash=pkg['sha1sums'][index], file=source,
                        type='sha1sum')
                hash.save()
            if pkg['sha256sums']:
                hash = PackageHash(hash=pkg['sha256sums'][index], file=source,
                        type='sha256sum')
                hash.save()
            if pkg['sha384sums']:
                hash = PackageHash(hash=pkg['sha384sums'][index], file=source,
                        type='sha384sum')
                hash.save()
            if pkg['sha512sums']:
                hash = PackageHash(hash=pkg['sha512sums'][index], file=source,
                        type='sha512sum')
                hash.save()

        comment = Comment(package=package, user=request.user,
                message=form.cleaned_data['comment'],
                ip=request.META['REMOTE_ADDR'], commit=True,)
        comment.save()
        return HttpResponseRedirect(
                reverse('aur-package_detail', args=[package.name,]))
    else:
        form = PackageSubmitForm()

    return render_to_response('aur/submit.html', {
        'user': request.user,
        'form': form,
    })

def comment(request, object_id):
    if request.POST and 'message' in request.POST:
        package = get_object_or_404(Package, name=object_id)
        comment = Comment(package=package, user=request.user,
                message=request.POST['message'],
                ip=request.META['REMOTE_ADDR'])
        if 'reply_to' in request.POST:
            comment.parent=request.POST['reply_to']
        comment.save()
        return HttpResponseRedirect(package.get_absolute_url())
    elif 'reply_to' in request.POST:
        return render_to_response('aur/comment_form.html', {
            'user': request.user,
            'package_id': object_id,
            'reply_to': request.POST['reply_to'],
        })
    else:
        return HttpResponseRedirect(
                reverse('aur-package_detail', args=[object_id,]))

def flag_out_of_date(request, object_id):
    package = get_object_or_404(Package, name=object_id)
    package.outdated = True
    package.save()
    return HttpResponseRedirect(reverse('aur-package_detail',
        args=[object_id,]))
