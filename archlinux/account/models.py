from django.db import models
from django.contrib.auth.models import User
from django import newforms as forms

class RegistrationForm(forms.Form):
    username = forms.CharField(max_length=30)
    first_name = forms.CharField(max_length=30)
    last_name = forms.CharField(max_length=30)
    email = forms.EmailField(max_length=75)
    password = forms.CharField(max_length=30, widget=forms.PasswordInput)
