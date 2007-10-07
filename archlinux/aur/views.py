from django.shortcuts import render_to_response
from django import newforms as forms # This will change to forms in 0.68 or 1.0

from archlinux.aur.models import Package, PackageSearchForm

def search(request, query = ''):
    context = dict()
    if request.method == 'GET':
        if request.GET.has_key('query'):
            # take the q GET var over the one passed on the URL
            query = request.GET['query'].strip()

        form = PackageSearchForm(request.GET)
        # If there are any errors in the forum, render the template and exit
        if not form.is_valid():
            return render_to_response('aur/search.html', {'form': form})

    else:
        form = PackageSearchForm()

    return render_to_response('aur/search.html', {'form': form})
