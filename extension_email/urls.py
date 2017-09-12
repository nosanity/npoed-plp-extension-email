# coding: utf-8

from django.conf.urls import url
from extension_email import views


urlpatterns = [
    url(r'^from_support/?$', views.FromSupportView.as_view(), name='from-support'),
    url(r'^from_support/confirm/?$', views.confirm_sending, name='from-support-confirm'),
    url(r'^from_support/analytics/?$', views.MassMailAnalytics.as_view(), name='massmail-analytics'),
    url(r'^unsubscribe/(?P<hash_str>.+)/?', views.unsubscribe, name='bulk-unsubscribe'),
    url(r'^unsubscribe-v2/(?P<hash_str>.+)/?', views.unsubscribe_v2, name='bulk-unsubscribe-v2'),
    url(r'^api/optout_status/?$', views.OptoutStatusView.as_view(), name='api-optout-status'),
    url(r'^support_mail_template/?$', views.support_mail_template, name='support_mail_template'),
]

