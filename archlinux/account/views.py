from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.shortcuts import render_to_response
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect

from archlinux.account.models import RegistrationForm
from archlinux.aur.models import Package

def register(request):
    # Are we submitting or just displaying?
    if request.method == 'POST':
        form = RegistrationForm(request.POST)

        if not form.is_valid():
            return render_to_response('registration/register.html', {'form': form, 'user': request.user})

        # Create the user
        user = User.objects.create_user(
            form.cleaned_data["username"],
            form.cleaned_data["email"],
            form.cleaned_data["password"]
        )
        user.first_name = form.cleaned_data["first_name"]
        user.last_name = form.cleaned_data["last_name"]
        user.save()
        return HttpResponseRedirect(reverse(profile))

    form = RegistrationForm()
    return render_to_response('registration/register.html', {'form': form, 'user': request.user})

@login_required
def profile(request):
    packages = Package.objects.filter(maintainers__username__exact=request.user.username)
    form = RegistrationForm()

    return render_to_response('registration/profile.html', {
        'packages': packages,
        'user': request.user,
        'form': form,
    })
