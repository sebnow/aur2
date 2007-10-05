from django.http import HttpResponse
from django.template import Context, loader
from django import newforms as forms # This will change to forms in 0.68 or 1.0

from archlinux.aur.models import Package PackageSearchForm

def search(request, query = ''):
    context = dict()
    if request.method == 'GET':
        if request.GET.has_key('query'):
            # take the q GET var over the one passed on the URL
            query = request.GET['query'].strip()

#    form_data = {
#            'query':        query,
#            'repository':   request.GET.get('repo', 'all'),
#            'category':     request.GET.get('category', 'all'),
#            'lastupdate':   request.GET.get('lastupdate', ''),
#            'limit':        int(request.GET.get('limit', '50')),
#            'sortby':       request.GET.get('sortby', ''),
#            'searchby':     request.GET.get('sortorder', ''),
#            'searchby':     request.GET.get('searchby', 'name'),
#    }

#    form = PackageSearchForm(form_data)
        form = PackageSearchForm(request.GET)
        # If there are any errors in the forum, render the template and exit
        if not form.is_valid():
            return render_to_response('aur/search.html', {'form': form})

    else:
        form = PackageSearchForm()

    context['form'] = form;
    return render_to_response('aur/search.html', Context(Context))
