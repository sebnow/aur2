from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.shortcuts import render_to_response
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect

from archlinux.account.forms import RegistrationForm, ProfileUpdateForm
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
def update_profile(request):
    if request.method != 'POST':
        return HttpResponseRedirect(reverse(profile))

    form = ProfileUpdateForm(request.POST)

    if not form.is_valid():
        return HttpResponseRedirect(reverse(profile))

    if form.cleaned_data["first_name"] and form.cleaned_data["first_name"] != request.user.first_name:
        request.user.first_name = form.cleaned_data["first_name"]
    if form.cleaned_data["last_name"] and form.cleaned_data["last_name"] != request.user.last_name:
        request.user.last_name = form.cleaned_data["last_name"]
    if form.cleaned_data["email"] and form.cleaned_data["email"] != request.user.email:
        request.user.email = form.cleaned_data["email"]
    if form.cleaned_data["password"] and form.cleaned_data["password"] == form.cleaned_data["password_repeat"]:
        request.user.set_password(form.cleaned_data["password"])

    request.user.save()
    return HttpResponseRedirect(reverse(profile))

@login_required
def profile(request):
    packages = Package.objects.filter(maintainers__username__exact=request.user.username)
    form = ProfileUpdateForm({
        'first_name': request.user.first_name,
        'last_name': request.user.last_name,
        'email': request.user.email,
    })

    return render_to_response('registration/profile.html', {
        'packages': packages,
        'packages_out_of_date': packages.filter(outdated=True).count(),
        'user': request.user,
        'form': form,
    })
