from re import sub
import os
import sys
import tarfile
import hashlib

from django.shortcuts import render_to_response, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect
from BetterPaginator import BetterPaginator
from django import newforms as forms # This will change to forms in 0.68 or 1.0
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.core import serializers
from django.utils.translation import ugettext

from archlinux.aur.models import *
from archlinux.aur.forms import PackageSearchForm, PackageSubmitForm

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
    # Get sorting variables from query string or fallback on defaults
    if request.GET.has_key('sortby'):
        sortby = request.GET['sortby']
        if sortby == 'maintainer':
            sortby = 'name'
    else:
        sortby = 'name'
    if request.GET.has_key('order') and request.GET['order'] == 'desc':
        sortby = "".join(('-', sortby))
    # Sort the results
    results = results.order_by(sortby, 'repository', 'category', 'name')
    # If we only got one hit, just go to the package's detail page
    if form.is_bound and results.count() == 1:
        return HttpResponseRedirect(reverse('aur-package_detail',
            args=[results[0].name,]))
    # Replace the current page with the new one if it's already in GET
    full_path = request.get_full_path()
    if request.GET.has_key('page'):
        link_template = sub(r'page=\d+', 'page=%d', request.get_full_path())
    elif full_path.find('?') >= 0:
        link_template = full_path + '&page=%d'
    else:
        link_template = full_path + '?page=%d'
    # Initialise the pagination
    paginator = BetterPaginator(results, int(form.get_or_default('limit')), link_template)
    paginator.set_page(int(request.GET.get('page', '1')))

    return render_to_response('aur/search.html', {
        'form': form,
        'packages': paginator.get_page(),
        'pager': paginator,
        'user': request.user,
        'request': request,
    })

# TODO: Implement transactions
@login_required
def submit(request):
    if request.method == 'POST':
        form = PackageSubmitForm(request.POST, request.FILES)
        if form.is_valid():
            form.save(request.user)
            return HttpResponseRedirect(reverse('aur-package_detail',
                args=[form.cleaned_data['package']['name'],]))
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
    return HttpResponseRedirect(package.get_absolute_url())

@login_required
def notify_of_updates(request, object_id):
    """Subscribe a user to package updates"""
    package = get_object_or_404(Package, name=object_id)
    PackageNotification(package=package, user=request.user).save()
    return HttpResponseRedirect(package.get_absolute_url())

@login_required
def denotify_of_updates(request, object_id):
    """Unsubscribe a user from package updates"""
    PackageNotification.objects.get(package__name=object_id, user=request.user).delete()
    return HttpResponseRedirect(reverse('aur-package_detail',
        args=[object_id,]))

def api_search(request, query):
    results = Package.objects.filter(name__icontains=query)
    data = serializers.serialize('json', results,
            fields=(
                'name',
                'version',
                'respository__name',
                'description'
            )
    )
    return HttpResponse(data, mimetype="text/plain")

@login_required
def manage_packages(request):
    if request.method != 'POST':
        return HttpResponseRedirect(reverse('aur-search'))
    packages = request.POST.getlist('packages')
    if request.POST['action'] == 'unflag-ood':
        for package_name in packages:
            package = Package.objects.get(name=package_name)
            if request.user.get_profile().can_modify_package(package):
                package.outdated = False
                package.save()
            else:
                return render_to_response('aur/error.html', dict(
                    heading = ugettext("Permission denied"),
                    error = "You are not allowed to edit %s" % package_name,
                ))
    elif request.POST['action'] == 'flag-ood':
        for package_name in packages:
            package = Package.objects.get(name=package_name)
            if request.user.get_profile().can_modify_package(package):
                package.outdated = True
                package.save()
            else:
                return render_to_response('aur/error.html', dict(
                    heading = ugettext("Permission denied"),
                    error = "You are not allowed to edit %s" % package_name,
                ))
    elif request.POST['action'] == 'disown':
        for package_name in packages:
            package = Package.objects.get(name=package_name)
            if request.user.get_profile().can_modify_package(package):
                package.maintainers.clear()
            else:
                return render_to_response('aur/error.html', dict(
                    heading = ugettext("Permission denied"),
                    error = "You cannot disown %s" % package_name,
                ))
    elif request.POST['action'] == 'adopt':
        for package_name in packages:
            package = Package.objects.get(name=package_name)
            if package.maintainers.count() == 0:
                package.maintainers.add(request.user)
            elif request.user.get_profile().is_moderator():
                package.maintainers.add(request.user)
            else:
                return render_to_response('aur/error.html', dict(
                    heading = ugettext("Permission denied"),
                    error = "You cannot adopt %s" % package_name,
                ))
    elif request.POST['action'] == 'delete':
        for package_name in packages:
            package = Package.objects.get(name=package_name)
            if request.user.get_profile().can_delete_package(package):
                package.delete()
            else:
                return render_to_response('aur/error.html', dict(
                    heading = ugettext("Permission denied"),
                    error = "You are not allowed to delete %s" % package_name,
                ))
    return HttpResponseRedirect(request.META['HTTP_REFERER'])

def api_package_info(request, object_id):
    package = get_object_or_404(Package, name=object_id)
    data = serializers.serialize('json', [package,])
    return HttpResponse(data, mimetype="text/plain")

def api_package_comments(request, object_id):
    comments = Comment.objects.filter(package=object_id)
    data = serializers.serialize('json', comments)
    return HttpResponse(data, mimetype="text/plain")

