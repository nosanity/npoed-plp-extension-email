# coding: utf-8

from django.db import models
from django.dispatch import receiver, Signal
from django.utils.translation import ugettext_lazy as _
from jsonfield import JSONField
from post_office.models import Email, STATUS
from plp.models import User

emails_sent_signal = Signal(providing_args=['status', 'ids'])


class SupportEmail(models.Model):
    """
    Модель для сохранения информации и настроек массовой рассылки
    """
    sender = models.ForeignKey(User, verbose_name=_('Отправитель'), on_delete=models.CASCADE)
    target = JSONField(blank=True, null=True)
    subject = models.CharField(max_length=128, blank=True, verbose_name=_('Тема'))
    html_message = models.TextField(null=True, blank=True, verbose_name=_('HTML письма'))
    text_message = models.TextField(null=True, blank=True, verbose_name=_('Текст письма'))
    confirmed = models.BooleanField(verbose_name=_('Отправка подтверждена'), default=True)
    to_myself = models.BooleanField(default=False, verbose_name=_('Сообщение только себе'))
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    unsubscriptions = models.PositiveIntegerField(default=0, verbose_name=_('Количество отписавшихся'))
    recipients_number = models.PositiveIntegerField(default=0, verbose_name=_('Количество получателей'))
    delivered_number = models.PositiveIntegerField(default=0, verbose_name=_('Доставлено писем'))

    class Meta:
        verbose_name = _('Рассылка')
        verbose_name_plural = _('Рассылки')

    def __str__(self):
        return '%s - %s' % (self.sender, self.subject)

    def get_recipients(self):
        from .utils import filter_users
        if self.target:
            return filter_users(self)[0]
        return []


class BulkEmailOptout(models.Model):
    user = models.ForeignKey(User, verbose_name=_('Пользователь'), related_name='bulk_email_optout',
                             on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True,
                                      verbose_name=_('Когда пользователь отписался от рассылки'))

    class Meta:
        verbose_name = _('Отписка от рассылок')
        verbose_name_plural = _('Отписки от рассылок')


class SupportEmailTemplate(models.Model):
    slug = models.CharField(max_length=128, verbose_name=_('Название шаблона'), unique=True)
    subject = models.CharField(max_length=128, verbose_name=_('Тема'))
    html_message = models.TextField(verbose_name=_('HTML письма'))
    text_message = models.TextField(null=True, blank=True, verbose_name=_('Текст письма'))

    def __str__(self):
        return self.slug

    class Meta:
        verbose_name = _('Шаблон рассылки')
        verbose_name_plural = _('Шаблоны рассылок')


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


@receiver(emails_sent_signal)
def update_delivered_number(sender, **kwargs):
    status = kwargs['status']
    ids = kwargs['ids']
    if status == STATUS.sent:
        for item in EmailRelated.objects.filter(id__in=ids).values('mass_mail_id').annotate(num=models.Count('id')):
            SupportEmail.objects.filter(id=item['mass_mail_id']).update(
                delivered_number=models.F('delivered_number') + item['num'])
