from re import sub

from django.shortcuts import render_to_response
from BetterPaginator import BetterPaginator
from django import newforms as forms # This will change to forms in 0.68 or 1.0

from archlinux.aur.models import Package, PackageSearchForm

def search(request, query = ''):
    if request.method == 'GET' and request.GET.has_key('query'):
        form = PackageSearchForm(request.GET)
        # If there are any errors in the forum, render the template and exit
        if not form.is_valid():
            return render_to_response('aur/search.html', {'form': form})
        
        # Find the packages by searching description and package name or maintainer
        if form.cleaned_data["searchby"] == 'maintainer':
            res1 = Package.objects.filter(maintainers__username__icontains=form.cleaned_data["query"])
        else:
            res1 = Package.objects.filter(name__icontains=form.cleaned_data["query"])
        res2 = Package.objects.filter(description__icontains=form.cleaned_data["query"])
        results = res1 | res2

    else:
        form_data = {
            'repository': 'all',
            'category': 'all',
            'searchby': 'name',
            'sortby': 'name',
            'order': 'asc',
            'limit': '25',
        }
        form = PackageSearchForm(form_data)

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
        link_template = 'page=%s'
    # Initialise the pagination
    paginator = BetterPaginator(results, int(form.cleaned_data["limit"]), link_template)
    paginator.set_page(int(request.GET.get('page', '1')))

    return render_to_response('aur/search.html', {
        'form': form,
        'packages': paginator.get_page(),
        'pager': paginator,
    })
