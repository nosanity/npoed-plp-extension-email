# coding: utf-8

from datetime import date
from django import forms
from django.core.validators import validate_email
from django.db.models import Case, When, Value, QuerySet, Model
from django.db.models.fields import BooleanField
from django.contrib.admin.widgets import FilteredSelectMultiple, AdminDateWidget
from django.template import Template, Context
from django.utils import timezone
from django.utils.six import text_type
from django.utils.translation import ugettext_lazy as _
from plp.models import CourseSession, Course, University
from .models import SupportEmail, SupportEmailTemplate


class CustomUnicodeCourseSession(CourseSession):
    class Meta:
        proxy = True
        ordering = []

    def __unicode__(self):
        now = timezone.now()
        d = {
            'univ': self.course.university.abbr,
            'course': self.course.title,
            'session': self.slug,
        }
        if self.datetime_starts and self.datetime_ends and self.datetime_starts < now < self.datetime_ends:
            week = (timezone.now().date() - self.datetime_starts.date()).days / 7 + 1
            return u'{univ} - {course} - {session} (неделя {week})'.format(week=week, **d)
        elif self.datetime_starts and self.datetime_starts > now:
            return u'{univ} - {course} - {session} (старт {date})'.format(date=now.strftime('%d.%m.%Y'), **d)
        else:
            return u'{univ} - {course} - {session}'.format(**d)

    @staticmethod
    def get_ordered_queryset():
        now = timezone.now()
        return CustomUnicodeCourseSession.objects.annotate(
            current=Case(
                When(datetime_starts__lt=now, datetime_ends__gt=now, then=Value(True)),
                default=Value(False),
                output_field=BooleanField()
            ),
            future=Case(
                When(datetime_starts__gt=now, then=Value(True)),
                default=False,
                output_field=BooleanField()
            )
        ).order_by('-current', '-future', '-datetime_starts')


class BulkEmailForm(forms.ModelForm):
    """
    Форма для создания массовой рассылки с определенными настройками
    """
    DATETIME_FORMAT = '%d.%m.%Y'
    MIN_DATE = '01.01.2000'
    MAX_DATE = '01.01.2030'
    ENROLLMENT_TYPE_INITIAL = ['paid', 'free']
    INSTRUCTOR_FILTER_CHOICES = [
        ('', _(u'Всем')),
        ('exclude', _(u'Не включать преподавателей')),
        ('only', _(u'Только преподавателям')),
    ]
    FILTER_TYPE_CHOICES = [
        ('email', _(u'По списку емейлов')),
        ('file', _(u'По списку емейлов из файла')),
        ('default', _(u'По фильтрам')),
    ]

    chosen_template = forms.ModelChoiceField(
        queryset=SupportEmailTemplate.objects.all(),
        required=False,
        label=_(u'Выберите шаблон или напишите письмо'),
        help_text=_(u'Имейте в виду, что вы не сможете редактировать выбранный шаблон')
    )
    filter_type = forms.ChoiceField(widget=forms.RadioSelect(attrs={'class': 'type-selector'}),
                                    label=_(u'Тип рассылки'),
                                    choices=FILTER_TYPE_CHOICES)
    emails = forms.FileField(
        widget=forms.FileInput(attrs={'data-field-type': 'file'}),
        required=False,
        label=_(u'Список емейлов'),
        help_text=_(u'Рассылка по списку игнорируя фильтры. Каждый адрес с новой строки.')
    )
    emails_list = forms.CharField(
        widget=forms.Textarea(attrs={'data-field-type': 'email', 'style': 'width: 100%'}),
        label=_(u'Список емейлов plaintext'),
        required=False,
        help_text=_(u'Список емейлов, разделенных точкой с запятой или переводом строки'))
    session_filter = forms.ModelMultipleChoiceField(
        queryset=CustomUnicodeCourseSession.get_ordered_queryset(),
        widget=FilteredSelectMultiple(verbose_name=_(u'Сессии'),
                                      is_stacked=False,
                                      attrs={'style': 'min-height: 180px', 'data-field-type': 'default'}),
        required=False,
        label=_(u'Сессия курса')
    )
    course_filter = forms.ModelMultipleChoiceField(
        queryset=Course.objects.all(),
        widget=FilteredSelectMultiple(verbose_name=_(u'Курсы'),
                                      is_stacked=False,
                                      attrs={'style': 'min-height: 180px', 'data-field-type': 'default'}),
        required=False,
        label=_(u'Курс'),
        help_text=_(u'Отправить письмо подписанным на новости курсов или записанным на них')
    )
    university_filter = forms.ModelMultipleChoiceField(
        queryset=University.objects.all(),
        widget=FilteredSelectMultiple(verbose_name=_(u'Вузы'),
                                      is_stacked=False,
                                      attrs={'style': 'min-height: 180px', 'data-field-type': 'default'}),
        required=False,
        label=_(u'Вуз'),
        help_text=_(u'Отправить письмо подписанным на новости курсов и записанным на курсы этих вузов')
    )
    to_myself = forms.Field(widget=forms.CheckboxInput(attrs={'data-field-type': 'default'}),
                            label=_(u'Отправить только себе'), required=False,
                            help_text=_(u'Вы получите письмо при отправке только себе даже если вы отписаны от рассылки'))
    instructors_filter = forms.ChoiceField(widget=forms.RadioSelect(attrs={'data-field-type': 'default'}),
                                           label=_(u'Отфильтровать преподавателей'),
                                           choices=INSTRUCTOR_FILTER_CHOICES, initial='', required=False)
    last_login_from = forms.DateField(label=_(u'Дата последнего входа от'),
                                      widget=AdminDateWidget(attrs={'data-field-type': 'default'}),
                                      input_formats=[DATETIME_FORMAT], initial=MIN_DATE)
    last_login_to = forms.DateField(label=_(u'Дата последнего входа до'),
                                    widget=AdminDateWidget(attrs={'data-field-type': 'default'}),
                                    input_formats=[DATETIME_FORMAT], initial=MAX_DATE)
    register_date_from = forms.DateField(label=_(u'Дата регистрации от'),
                                         widget=AdminDateWidget(attrs={'data-field-type': 'default'}),
                                         input_formats=[DATETIME_FORMAT], initial=MIN_DATE)
    register_date_to = forms.DateField(label=_(u'Дата регистрации до'),
                                       widget=AdminDateWidget(attrs={'data-field-type': 'default'}),
                                       input_formats=[DATETIME_FORMAT], initial=MAX_DATE)
    enrollment_type = forms.MultipleChoiceField(
        choices=(('paid', _(u'Платники')), ('free', _(u'Бесплатники'))),
        widget=forms.CheckboxSelectMultiple(attrs={'data-field-type': 'default'}),
        label=_(u'Вариант прохождения'), initial=ENROLLMENT_TYPE_INITIAL)
    got_certificate = forms.MultipleChoiceField(
        choices=(
            ('paid', _(u'Пользователь получил подтвержденный сертификат')),
            ('free', _(u'Пользователь получил неподтвержденный сертификат')),
        ),
        widget=forms.CheckboxSelectMultiple(attrs={'data-field-type': 'default'}),
        label=_(u'Получен сертификат'), required=False,
        help_text=_(u'Если не выбран ни один из чекбоксов - рассылка для всех пользователей, которые и получили, '
                   u'и не получили сертификаты. Если выбран один чекбокс - то только пользователям платникам либо '
                   u'бесплатникам, получившим сертификат. Если оба - то всем пользователям, получившим сертификат'))

    def __init__(self, *args, **kwargs):
        super(BulkEmailForm, self).__init__(*args, **kwargs)
        self.fields['subject'].required = True
        self.fields['html_message'].required = True
        # chosen_template first
        chosen_template = self.fields.pop('chosen_template')
        root = self.fields._OrderedDict__root
        first = root[1]
        root[1] = first[0] = self.fields._OrderedDict__map['chosen_template'] = [root, first, 'chosen_template']
        dict.__setitem__(self.fields, 'chosen_template', chosen_template)

    def to_json(self):
        data = getattr(self, 'cleaned_data', {})
        result = {}
        for k, v in data.iteritems():
            if k in self.Meta.fields:
                continue
            if isinstance(v, date):
                result[k] = v.strftime(self.DATETIME_FORMAT)
            elif isinstance(v, QuerySet):
                result[k] = [int(i.pk) for i in v]
            elif isinstance(v, Model):
                result[k] = v.pk
            else:
                result[k] = v
        return result

    def clean_emails(self):
        val = self.cleaned_data.get('emails')
        if self.cleaned_data.get('filter_type', '') == 'file' and not val:
            raise forms.ValidationError(_(u'Это поле оязательно.'))
        if val:
            result = [i.strip() for i in val.readlines() if i.strip()]
            try:
                text_type(result[0])
            except (UnicodeDecodeError, IndexError):
                raise forms.ValidationError(_(u'Файл не содержит данных или некорректен'))
            return result

    def _validate_emails(self, emails):
        incorrect = []
        for e in emails:
            try:
                validate_email(e)
            except forms.ValidationError:
                incorrect.append(e)
        return incorrect

    def clean_emails_list(self):
        val = self.cleaned_data.get('emails_list')
        if self.cleaned_data.get('filter_type', '') == 'email' and not val:
            raise forms.ValidationError(_(u'Это поле оязательно.'))
        if val:
            emails = [i.strip() for i in val.splitlines() if i.strip()]
            emails = [[j.strip() for j in i.split(';') if j.strip()] for i in emails]
            emails = reduce(lambda x, y: x + y, emails, [])
            incorrect = self._validate_emails(emails)
            if incorrect:
                raise forms.ValidationError(_(u'Следующие емейлы некорректны: %s') % ', '.join(incorrect))
            if not emails:
                raise forms.ValidationError(_(u'Значение не должно состоять из одних пробелов'))
            return emails

    def clean_html_message(self):
        """
        Проверка того, что в HTML тексте корректный джанго шаблон
        """
        html = self.cleaned_data.get('html_message')
        if html:
            try:
                Template(html).render(Context({}))
            except:
                raise forms.ValidationError(_(u'Некорректный HTML текст письма'))
        return html
    
    def _post_clean(self):
        super(BulkEmailForm, self)._post_clean()
        chosen_filter_type = self.cleaned_data.get('filter_type')
        for name, field in self.fields.items():
            if field.widget.attrs.get('data-field-type') in dict(self.FILTER_TYPE_CHOICES) and \
                    field.widget.attrs.get('data-field-type') != chosen_filter_type:
                # не учитываем поля не подходящие по типу рассылки (по емейлу/фильтрам)
                self._errors.pop(name, None)
                self.cleaned_data[name] = field.to_python(field.initial)

    def clean(self):
        data = super(BulkEmailForm, self).clean()
        last_login_from = data.get('last_login_from')
        last_login_to = data.get('last_login_to')
        register_date_from = data.get('register_date_from')
        register_date_to = data.get('register_date_to')
        errors = []
        if last_login_from and last_login_to and last_login_from > last_login_to:
            errors.append(_(u'Невозможно отправить рассылку - проверьте корректность дат регистрации'))
        if register_date_from and register_date_to and register_date_from > register_date_to:
            errors.append(_(u'Невозможно отправить рассылку - проверьте корректность дат последнего входа'))
        if errors:
            self._update_errors(forms.ValidationError({'__all__': errors}))
        return data

    class Meta:
        model = SupportEmail
        fields = ['subject', 'html_message']
        widgets = {
            'subject': forms.TextInput(attrs={'style': 'width: 100%'}),
            'html_message': forms.Textarea(attrs={'style': 'width: 100%', 'class': 'vLargeTextField'}),
        }
        help_texts = {
            'html_message': _(u'Можно использовать переменные {{ user.get_full_name }} для подстановки '
                              u'имени и фамилии пользователя в текст, {{ user.first_name }} - имени, '
                              u'{{ user.last_name }} - фамилии, {{ user.email }} - email')
        }

    class Media:
        css = {'all': ['admin/css/widgets.css']}
        js = ['/admin/jsi18n/']
