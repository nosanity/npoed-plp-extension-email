# coding: utf-8

import codecs
import csv
import logging
import tempfile
import time
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.translation import ugettext as _
from celery import task
from emails.django import Message
from .models import SupportEmail
from .notifications import BulkEmailSend


@task
def support_mass_send(obj_id):
    """
    Сначала создаются объекты SupportEmailStatus для всех получателей,
    потом вызывается команда send_support_mail, которая работает как send_queued_mail
    из post_office за исключением того, что здесь не сохраняется текст письма для каждого
    из пользователей, письмо генерируется и отправляется, используя шаблон из SupportEmail
    """
    SupportEmail.objects.get(id=obj_id).prepare_mass_send()


@task
def send_analytics_data(user_id):
    user = get_user_model().objects.get(id=user_id)
    data = prepare_analytics_data()
    dt = timezone.localtime(timezone.now()).strftime('%Y_%m_%d__%H_%M')
    with tempfile.SpooledTemporaryFile(mode='w') as tmp:
        tmp.write(data)
        tmp.seek(0)
        m = Message(subject=_('Аналитика по массовым рассылкам'),
                    text=_('Аналитика по массовым рассылкам'),
                    mail_from=settings.EMAIL_NOTIFICATIONS_FROM,
                    mail_to=user.email)
        m.attach(filename='email_analytics_{}.csv'.format(dt), data=tmp)
        m.send()


def prepare_analytics_data():
    headers = (_('Дата рассылки'), _('Время рассылки'), _('Тема рассылки'),
               _('Размер базы'), _('Количество доставленных писем'), _('Количество отписок'))
    qs = SupportEmail.objects.order_by('-created')
    with tempfile.SpooledTemporaryFile(mode='w') as csv_file:
        csv_file.write(codecs.BOM_UTF8.decode('utf8'))
        writer = csv.writer(csv_file, delimiter=';')
        writer.writerow(headers)
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
            writer.writerow(row)
        csv_file.seek(0)
        return csv_file.read()
