# coding: utf-8

from django import forms
from django.contrib import admin
from dal.autocomplete import ModelSelect2
from .models import SupportEmail, BulkEmailOptout, SupportEmailTemplate


user_autocomplete_widget = ModelSelect2(
    url='user-autocomplete', attrs={'data-theme': 'classic', 'style': 'min-width: 300px;'}
)


class SupportEmailAdminForm(forms.ModelForm):
    class Meta:
        model = SupportEmail
        fields = '__all__'
        widgets = {
            'sender': user_autocomplete_widget,
        }


@admin.register(SupportEmail)
class SupportEmailAdmin(admin.ModelAdmin):
    list_display = ('sender', 'subject', 'created', 'confirmed', )
    form = SupportEmailAdminForm


class BulkEmailOptoutAdminForm(forms.ModelForm):
    class Meta:
        model = BulkEmailOptout
        fields = '__all__'
        widgets = {
            'user': user_autocomplete_widget,
        }


@admin.register(BulkEmailOptout)
class BulkEmailOptoutAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at')
    form = BulkEmailOptoutAdminForm


@admin.register(SupportEmailTemplate)
class SupportEmailTemplateAdmin(admin.ModelAdmin):
    list_display = ('slug', 'subject', )
