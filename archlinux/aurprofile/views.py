from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.shortcuts import render_to_response
from django.template import RequestContext

from aurprofile.forms import ProfileUpdateForm
from aur.models import Package

@login_required
def profile(request):
    packages = Package.objects.filter(maintainers=request.user)
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
    else:
        form = ProfileUpdateForm(instance=request.user)
    count_packages_ood = packages.filter(outdated=True).count()
    context = RequestContext(request, {
        'packages': packages,
        'form': form,
        'packages_out_of_date': count_packages_ood,
    })
    return render_to_response('aurprofile/profile.html', context)
