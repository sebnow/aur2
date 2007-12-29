from re import sub
import os

from django.shortcuts import render_to_response, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect
from BetterPaginator import BetterPaginator
from django import newforms as forms # This will change to forms in 0.68 or 1.0
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.db import transaction

from archlinux.aur.models import *
import archlinux.aur.Package as PKGBUILD
import datetime

def search(request, query = ''):
    if request.method == 'GET' and request.GET.has_key('query'):
        form = PackageSearchForm(request.GET)
        # If there are any errors in the forum, render the template and exit
        if not form.is_valid():
            return render_to_response('aur/search.html', {'form': form})

        # Find the packages by searching description and package name or maintainer
        if form.cleaned_data["query"] != '':
            if form.cleaned_data["searchby"] == 'maintainer':
                results = Package.objects.filter(maintainers__username__icontains=form.cleaned_data["query"])
            else:
                res1 = Package.objects.filter(name__icontains=form.cleaned_data["query"])
                res2 = Package.objects.filter(description__icontains=form.cleaned_data["query"])
                results = res1 | res2
        else:
            results = Package.objects.all()

    else:
        form = PackageSearchForm()

        # We need to validate to get form.cleaned_data
        if not form.is_valid():
            return render_to_response('aur/search.html', {'form': form})

        results = Package.objects.all()

    # Restrict results
    if form.cleaned_data["repository"] != 'all':
        results = results.filter(repository__name__iexact=form.cleaned_data["repository"])
    if form.cleaned_data["category"] != 'all':
        results = results.filter(category__name__exact=form.cleaned_data["category"])
    if form.cleaned_data["lastupdate"]:
        results = results.filter(updated__gte=form.cleaned_data["lastupdate"])

    # Sort
    sortby = form.cleaned_data["sortby"]

    # Change the sort order if necessary
    if form.cleaned_data["order"] == 'desc':
        results = results.order_by('-' + sortby, 'repository', 'category', 'name')
    else:
        results = results.order_by(sortby, 'repository', 'category', 'name')

    # Take care of pagination
    # Replace the current page with the new one if it's already in GET
    if request.GET.has_key('page'):
        link_template = sub(r'page=\d+', 'page=%d', request.get_full_path())
    else:
        link_template = request.get_full_path() + '&page=%d'
    # Initialise the pagination
    paginator = BetterPaginator(results, int(form.cleaned_data["limit"]), link_template)
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

        # Save the uploaded file to disk
        fp = open(form.cleaned_data['file'].filename, "wb")
        fp.write(form.cleaned_data['file'].content)
        fp.close()

        try:
            pkg = PKGBUILD.Package(os.path.join(os.getcwd(),
                form.cleaned_data["file"].filename))
        except PKGBUILD.InvalidPackage, e:
            # TODO: Add error to form
            return render_to_response('aur/submit.html', {
                'user': request.user, 'form': form})

        # Check if we are updating an existing package or creating one

        package = Package(name=pkg['name'], version=pkg['version'],
                release=pkg['release'], description=pkg['description'],
                url=pkg['url'])

        package.maintainers.add(request.user)
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
                return render_to_response('aur/submit.html', {
                    'user': request.user,
                    'form': form,
                })
            else:
                package.depends.add(dep)

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
                })
            else:
                package.architectures.add(object)

        package.updated = datetime.datetime.now()
        package.added = datetime.datetime.now()

        # Save the package so we can reference it
        package.save()
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
                ip=request.META['REMOTE_ADDR'], commit=True,
                added=datetime.datetime.now())
        comment.save()
        return HttpResponseRedirect(
                reverse('django.views.generic.list_detail.object_detail',
                    args=[package.name,]))
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
                message=request.POST['message'], added=datetime.datetime.now(),
                ip=request.META['REMOTE_ADDR'])
        if 'reply_to' in request.POST:
            comment.parent=request.POST['reply_to']
        comment.save()
        return HttpResponseRedirect(
                reverse('django.views.generic.list_detail.object_detail',
                args=[object_id,]))
    elif 'reply_to' in request.POST:
        return render_to_response('aur/comment_form.html', {'user': request.user,
            'package_id': object_id, 'reply_to': request.POST['reply_to']})
    else:
        return HttpResponseRedirect(
                reverse('django.views.generic.list_detail.object_detail',
                args=[object_id,]))
