from archlinux.account.models import *
from django.contrib import admin

class ArchUserAdmin(admin.ModelAdmin):
    fields = ('user', 'is_inactive')

admin.site.register(ArchUser, ArchUserAdmin)

