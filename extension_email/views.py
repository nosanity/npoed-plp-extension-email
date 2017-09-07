# coding: utf-8

import base64
import logging
from django.conf import settings
from django.core.urlresolvers import reverse_lazy
from django.db.models import F
from django.http import Http404, JsonResponse, HttpResponse
from django.shortcuts import render
from django.template.loader import get_template
from django.utils.translation import ugettext as _, ungettext
from django.views.generic import CreateView, ListView
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from api.views.user import ApiKeyPermission
from plp.models import User
from .forms import BulkEmailForm
from .models import BulkEmailOptout, SupportEmailTemplate, SupportEmail
from .tasks import support_mass_send, send_analytics_data, prepare_analytics_data
from .utils import filter_users


class FromSupportView(CreateView):
    """
    Вьюха для создания и отправки массовых рассылок
    """
    form_class = BulkEmailForm
    success_url = reverse_lazy('frontpage')
    template_name = 'extension_email/main.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_staff:
            return super(FromSupportView, self).dispatch(request, *args, **kwargs)
        raise Http404

    def get_template_names(self):
        if getattr(settings, 'EXTENSION_EMAIL_OPENEDU_TEMPLATE', True):
            return [self.template_name]
        return ['extension_email/main_miptx.html']

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.sender = self.request.user
        self.object.target = form.to_json()
        self.object.save()
        support_mass_send.delay(self.object)
        return JsonResponse({'redirect_url': self.get_success_url()})

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        form_html = get_template('extension_email/_message_form.html').render(context={'form': form}, request=request)
        if form.is_valid():
            if '_check_users_count' in request.POST:
                item = form.save(commit=False)
                item.sender = self.request.user
                item.target = form.to_json()
                users, msg_type = filter_users(item)
                error = False
                if msg_type == 'to_myself':
                    msg = _(u'Вы уверены, что хотите отправить это сообщение себе?')
                elif msg_type == 'to_all':
                    msg = _(u'Вы хотите отправить письмо с темой "%(theme)s" всем пользователям. Продолжить?') % \
                          {'theme': item.subject}
                elif msg_type == 'error':
                    msg = _(u'Ошибка коммуникации с EDX')
                    error = True
                else:
                    msg = ungettext(
                        u'Вы хотите отправить письмо с темой "%(theme)s" %(user_count)s пользователю. Продолжить?',
                        u'Вы хотите отправить письмо с темой "%(theme)s" %(user_count)s пользователям. Продолжить?',
                        users.count()
                    ) % {'theme': item.subject, 'user_count': users.count()}
                return JsonResponse({
                    'form': form_html,
                    'valid': True,
                    'message': msg,
                    'error': error,
                })
            return self.form_valid(form)
        else:
            return JsonResponse({'form': form_html, 'valid': False})


class MassMailAnalytics(ListView):
    template_name = 'extension_email/analytics.html'
    model = SupportEmail
    paginate_by = 20
    queryset = SupportEmail.objects.all()
    ordering = ['-created']
    headers = (_(u'Дата рассылки'), _(u'Время рассылки'), _(u'Тема рассылки'),
               _(u'Размер базы'), _(u'Количество доставленных писем'), _(u'Количество отписок'))

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_staff:
            return super(MassMailAnalytics, self).dispatch(request, *args, **kwargs)
        raise Http404

    def get_context_data(self, **kwargs):
        data = super(MassMailAnalytics, self).get_context_data(**kwargs)
        data['headers'] = self.headers
        return data

    def post(self, request):
        items_count = self.get_queryset().count()
        # максимальное число строк которое можно выдать csv файлом синхронно
        max_sync_items = getattr(settings, 'SUPPORT_EMAIL_MAX_SYNC_ANALYTICS', 1000)
        if 'download' in request.POST:
            if items_count <= max_sync_items:
                result = prepare_analytics_data()
                resp = HttpResponse(result, content_type='text/csv; charset=utf8')
                resp['Content-Disposition'] = 'attachment; filename=%s' % 'email_analytics.csv'
                return resp
            else:
                send_analytics_data.delay(request.user.id)
                return JsonResponse({'status': 0})
        return JsonResponse({'sync': items_count <= max_sync_items})


def unsubscribe(request, hash_str):
    """
    отписка от рассылок по уникальному для пользователя хэшу
    """
    try:
        s = base64.b64decode(hash_str)
    except TypeError:
        raise Http404
    try:
        user = User.objects.get(username=s)
    except User.DoesNotExist:
        raise Http404
    obj_id = request.GET.get('id')
    if obj_id and not BulkEmailOptout.objects.filter(user=user).exists():
        try:
            SupportEmail.objects.filter(id=obj_id).update(unsubscriptions=F('unsubscriptions') + 1)
            logging.info('User %s unsubscribed from mass emails (obj_id %s)' % (request.user.email, obj_id))
        except (ValueError, UnicodeDecodeError) as e:
            logging.error('User %s unsubscribe from mass emails error %s' % (request.user.email, e))
    BulkEmailOptout.objects.get_or_create(user=user)
    context = {
        'profile_url': '{}/profile/'.format(settings.SSO_NPOED_URL),
    }
    return render(request, 'extension_email/unsubscribed.html', context)


def support_mail_template(request):
    """
    возвращает текст шаблона массовой рассылки
    """
    if not request.user.is_staff:
        raise Http404
    try:
        template = SupportEmailTemplate.objects.get(id=request.POST.get('id'))
    except (SupportEmailTemplate.DoesNotExist, ValueError):
        raise Http404
    return JsonResponse({
        'subject': template.subject,
        'text_message': template.text_message,
        'html_message': template.html_message,
    })


class OptoutStatusView(APIView):
    """
        **Описание**

            Ручка для проверки и изменения статуса подписки пользователя на информационные
            рассылки платформы. Требуется заголовок X-PLP-Api-Key.

        **Пример запроса**

            GET bulk_email/api/optout_status/?user=<username>

            POST bulk_email/api/optout_status/{
                "user" : username,
                 "status" : boolean
            }

        **Параметры post-запроса**

            * user: логин пользователя
            * status: True/False для активации/деактивации подписки соответственно

        **Пример ответа**

            * {
                  "status": True
              }

            новый статус подписки

            404 если пользователь не найден
            400 если переданы не все параметры

    """
    permission_classes = (ApiKeyPermission,)

    def get(self, request, *args, **kwargs):
        username = request.query_params.get('user')
        if username:
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                return Response(status=status.HTTP_404_NOT_FOUND)
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        optout = BulkEmailOptout.objects.filter(user=user).first()
        if optout:
            return Response({'status': False})
        else:
            return Response({'status': True})

    def post(self, request, *args, **kwargs):
        username = request.data.get('user')
        new_status = request.data.get('status')
        if isinstance(new_status, basestring):
            new_status = new_status.lower() != 'false'
        if not username or new_status is None:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        old_status = not BulkEmailOptout.objects.filter(user=user).exists()
        if new_status == old_status:
            return Response({'status': new_status})
        if new_status:
            BulkEmailOptout.objects.filter(user=user).delete()
        else:
            BulkEmailOptout.objects.create(user=user)
        return Response({'status': new_status})
