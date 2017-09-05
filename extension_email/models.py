# coding: utf-8

from django.db import models
from django.dispatch import receiver
from django.utils.translation import ugettext_lazy as _
from jsonfield import JSONField
from post_office.models import Email, STATUS
from plp.models import User


class SupportEmail(models.Model):
    """
    Модель для сохранения информации и настроек массовой рассылки
    """
    sender = models.ForeignKey(User, verbose_name=_(u'Отправитель'))
    target = JSONField(blank=True, null=True)
    subject = models.CharField(max_length=128, blank=True, verbose_name=_(u'Тема'))
    html_message = models.TextField(null=True, blank=True, verbose_name=_(u'HTML письма'))
    text_message = models.TextField(null=True, blank=True, verbose_name=_(u'Текст письма'))
    confirmed = models.BooleanField(verbose_name=_(u'Отправка подтверждена'), default=True)
    to_myself = models.BooleanField(default=False, verbose_name=_(u'Сообщение только себе'))
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    unsubscriptions = models.PositiveIntegerField(default=0, verbose_name=_(u'Количество отписавшихся'))
    recipients_number = models.PositiveIntegerField(default=0, verbose_name=_(u'Количество получателей'))
    delivered_number = models.PositiveIntegerField(default=0, verbose_name=_(u'Доставлено писем'))

    class Meta:
        verbose_name = _(u'Рассылка')
        verbose_name_plural = _(u'Рассылки')

    def __unicode__(self):
        return '%s - %s' % (self.sender, self.subject)

    def get_recipients(self):
        from .utils import filter_users
        if self.target:
            return filter_users(self)[0]
        return []


class BulkEmailOptout(models.Model):
    user = models.ForeignKey(User, verbose_name=_(u'Пользователь'), related_name='bulk_email_optout')
    created_at = models.DateTimeField(auto_now_add=True,
                                      verbose_name=_(u'Когда пользователь отписался от рассылки'))

    class Meta:
        verbose_name = _(u'Отписка от рассылок')
        verbose_name_plural = _(u'Отписки от рассылок')


class SupportEmailTemplate(models.Model):
    slug = models.CharField(max_length=128, verbose_name=_(u'Название шаблона'), unique=True)
    subject = models.CharField(max_length=128, verbose_name=_(u'Тема'))
    html_message = models.TextField(verbose_name=_(u'HTML письма'))
    text_message = models.TextField(null=True, blank=True, verbose_name=_(u'Текст письма'))

    def __unicode__(self):
        return self.slug

    class Meta:
        verbose_name = _(u'Шаблон рассылки')
        verbose_name_plural = _(u'Шаблоны рассылок')


class EmailRelated(Email):
    """
    Класс, наследуемый от post_office.models.Email с целью отслеживания доставки писем
    из определенной рассылки
    """
    mass_mail_id = models.PositiveIntegerField()

    @classmethod
    def create_from_parent_model(cls, item, mass_mail_id, commit=False):
        """
        создание объекта класса EmailRelated с копированием полей item и присвоением
        указанного mass_mail_id
        :param item: Email
        :param mass_mail_id: int
        :param commit: bool
        :return: EmailRelated
        """
        result = cls()
        for field in item._meta.fields:
            if field.auto_created:
                continue
            setattr(result, field.name, getattr(item, field.name))
        result.mass_mail_id = mass_mail_id
        if commit:
            result.save()
        return result


@receiver(models.signals.post_save, sender=Email)
def update_delivered_number(sender, instance, **kwargs):
    """
    Если этот объект Email имеет отношение к массовой рассылке, увеличиваем количество
    доставленных писем при успешном статусе
    """
    try:
        if instance.status == STATUS.sent and instance.emailrelated:
            SupportEmail.objects.filter(id=instance.emailrelated.mass_mail_id).update(
                delivered_number=models.F('delivered_number') + 1)
    except EmailRelated.DoesNotExist:
        pass
