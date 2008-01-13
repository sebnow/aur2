from django.db import models
from django.contrib.auth.models import User
from django import newforms as forms

class RegistrationForm(forms.Form):
    username = forms.CharField(max_length=30)
    first_name = forms.CharField(max_length=30)
    last_name = forms.CharField(max_length=30)
    email = forms.EmailField(max_length=75)
    password = forms.CharField(max_length=30, widget=forms.PasswordInput)
    irc_nick = forms.CharField(max_length=16, label='IRC Nick')

class ProfileUpdateForm(forms.Form):
    first_name = forms.CharField(max_length=30, required=False)
    last_name = forms.CharField(max_length=30, required=False)
    email = forms.EmailField(max_length=75, required=False)
    password = forms.CharField(max_length=30, widget=forms.PasswordInput, required=False, initial='')
    password_repeat = forms.CharField(max_length=30, widget=forms.PasswordInput, required=False, initial='')
    irc_nick = forms.CharField(max_length=16, label='IRC Nick')
