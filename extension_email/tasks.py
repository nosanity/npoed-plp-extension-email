# coding: utf-8

import codecs
import csv
import logging
import tempfile
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.translation import ugettext as _
from celery import task
from emails.django import Message
from .models import SupportEmail
from .notifications import BulkEmailSend


@task
def support_mass_send(obj):
    logging.info('%s Started sending bulk emails' % timezone.now().strftime('%H:%M:%S %d.%m.%Y'))
    msgs = BulkEmailSend(obj)
    msgs.send()
    logging.info('%s Ended sending bulk emails' % timezone.now().strftime('%H:%M:%S %d.%m.%Y'))


@task
def send_analytics_data(user_id):
    user = get_user_model().objects.get(id=user_id)
    data = prepare_analytics_data()
    with tempfile.SpooledTemporaryFile() as tmp:
        tmp.write(data)
        tmp.seek(0)
        m = Message(subject=_(u'Аналитика по массовым рассылкам'),
                    text=_(u'Аналитика по массовым рассылкам'),
                    mail_from=settings.EMAIL_NOTIFICATIONS_FROM,
                    mail_to=user.email)
        m.attach(filename='email_analytics.csv', data=tmp)
        m.send()


def prepare_analytics_data():
    def _encode(arr):
        return [unicode(cn).encode('utf-8', 'ignore') for cn in arr]

    headers = (_(u'Дата рассылки'), _(u'Время рассылки'), _(u'Тема рассылки'),
               _(u'Размер базы'), _(u'Количество доставленных писем'), _(u'Количество отписок'))
    qs = SupportEmail.objects.order_by('-created')
    with tempfile.SpooledTemporaryFile() as csv_file:
        csv_file.write(codecs.BOM_UTF8)
        writer = csv.writer(csv_file, delimiter=';')
        writer.writerow(_encode(headers))
        for item in qs:
            dt = timezone.localtime(item.created)
            row = [
                dt.strftime('%d.%m.%Y'),
                dt.strftime('%H:%M'),
                item.subject,
                str(item.recipients_number),
                str(item.delivered_number),
                str(item.unsubscriptions),
            ]
            writer.writerow(_encode(row))
        csv_file.seek(0)
        return csv_file.read()
