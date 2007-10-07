from django.shortcuts import render_to_response
from django import newforms as forms # This will change to forms in 0.68 or 1.0

from archlinux.aur.models import Package, PackageSearchForm

def search(request, query = ''):
    context = dict()
    if request.method == 'GET':

        form = PackageSearchForm(request.GET)
        # If there are any errors in the forum, render the template and exit
        if not form.is_valid():
            return render_to_response('aur/search.html', {'form': form})

        res1 = Package.objects.filter(name__icontains=form.cleaned_data["query"])
        res2 = Package.objects.filter(description__icontains=form.cleaned_data["query"])
        results = res1 | res2

    else:
        form = PackageSearchForm()
        results = Package.objects.all()

    if form.cleaned_data["repository"] != 'all':
        results = results.filter(repository__name__exact=form.cleaned_data["repository"])
    if form.cleaned_data["category"] != 'all':
        results = results.filter(category__name__exact=form.cleaned_data["category"])

    return render_to_response('aur/search.html', {'form': form, 'packages': results})
