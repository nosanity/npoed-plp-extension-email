# coding: utf-8

from django.conf import settings
from django.db.models import Q
from django.utils import timezone
from plp.models import User, EnrollmentReason, Participant, Subscription, Course, CourseSession, NewsSubscription, \
    LMSBackend
from plp.utils.edx_enrollment import EDXEnrollment, EDXEnrollmentError
from .forms import BulkEmailForm, CustomUnicodeCourseSession
from .models import BulkEmailOptout


class EdxEnrollmentWithPerms(EDXEnrollment):
    def get_permissions(self):
        return self.request(
            method='GET',
            path='/api/extended/credentials'
        )


def filter_users(support_email):
    """
    Фильтрация пользователей по данным модели массовой рассылки.
    Возвращает сет емейлов пользователей и тип фильтра ('to_all', 'to_myself' или '')
    """
    def _check_enrollment_type_chosen():
        return data['enrollment_type'] != BulkEmailForm.ENROLLMENT_TYPE_INITIAL

    def _check_get_certificate_chosen():
        return len(data['got_certificate'])

    data = support_email.target
    subscribed_emails = set()
    if data.get('subscribed'):
        subscribed_emails = set(NewsSubscription.objects.filter(confirmed=True, unsubscribed=False).
                                values_list('email', flat=True))
    if not data.get('filter_type') and data.get('subscribed'):
        return subscribed_emails, ''
    by_email = data.get('emails') or data.get('emails_list')
    if by_email:
        emails = set(User.objects.filter(email__in=by_email, bulk_email_optout__isnull=True, is_active=True).
                     values_list('email', flat=True))
        if data.get('subscribed'):
            emails = emails.union(subscribed_emails)
        return emails, ''
    if data.get('to_myself'):
        emails = {support_email.sender.email}
        if data.get('subscribed'):
            emails = emails.union(subscribed_emails)
            return emails, ''
        return emails, 'to_myself'
    dic = {'bulk_email_optout__isnull': True, 'is_active': True}
    dic_exclude = {}
    session_ids = []
    to_all = True

    # если фильтр по сессиям будет нужен, но пользователь не выбрал ни одной сессии
    if not data['session_filter'] and not data['course_filter'] and not data['university_filter'] \
            and (_check_enrollment_type_chosen() or _check_get_certificate_chosen()):
        data['session_filter'] = list(CourseSession.objects.values_list('id', flat=True))
    if data['session_filter']:
        to_all = False
        session_ids = data['session_filter']
        dic.update({'participants__session__id__in': session_ids})
    subscription_ids = None
    if data['course_filter'] or data['university_filter']:
        to_all = False
        ids = list(data['course_filter']) + \
              list(Course.objects.filter(university__id__in=data['university_filter']).values_list('id', flat=True))
        # не делаем рассылку по подписчикам, если указаны платники/бесплатники/сертификаты
        if not (_check_enrollment_type_chosen() or _check_get_certificate_chosen()):
            subscription_ids = Subscription.objects.filter(course__id__in=ids, active=True).\
                values_list('user__id', flat=True)
        ids = list(CourseSession.objects.filter(course__id__in=ids).values_list('id', flat=True))
        session_ids.extend(ids)
        session_ids = list(set(session_ids))
        dic.update({'participants__session__id__in': session_ids})

    instructor_usernames = []
    if data.get('instructors_filter', '') != '':
        to_all = False
        if getattr(settings, 'ENABLE_ARM', False):
            from arm.models import UserRoleInstance
            from arm.utils.role_templates import COURSE_AUTHOR_SLUG
            instructor_usernames = list(UserRoleInstance.objects.filter(role__slug=COURSE_AUTHOR_SLUG).
                                        values_list('user__username', flat=True).distinct())
        else:
            backend_ids = list(set(CourseSession.values_list('lms_id', flat=True).distinct()))
            backends = list(LMSBackend.objects.get(
                id__in=filter(None, backend_ids), core=LMSBackend.CORE_EDX, sso_push=True)
            )
            all_session_ids = [i.get_absolute_slug_v1() for i in CourseSession.objects.all()]
            for lms in backends:
                try:
                    for k, v in EdxEnrollmentWithPerms(lms).get_permissions().json().items():
                        instructor_usernames.extend(v if k in all_session_ids else [])
                except (EDXEnrollmentError, ValueError):
                    return User.objects.none(), 'error'
            instructor_usernames = list(set(instructor_usernames))

    last_login_from = data.get('last_login_from') or BulkEmailForm.MIN_DATE
    last_login_to = data.get('last_login_to') or BulkEmailForm.MAX_DATE
    register_date_from = data.get('register_date_from') or BulkEmailForm.MIN_DATE
    register_date_to = data.get('register_date_to') or BulkEmailForm.MAX_DATE
    if last_login_from != BulkEmailForm.MIN_DATE or last_login_to != BulkEmailForm.MAX_DATE:
        to_all = False
        dic.update({
            'last_login__gte': timezone.datetime.strptime(last_login_from, BulkEmailForm.DATETIME_FORMAT),
            'last_login__lte': timezone.datetime.strptime(last_login_to, BulkEmailForm.DATETIME_FORMAT) + timezone.timedelta(1,0,0),
        })
    if register_date_from != BulkEmailForm.MIN_DATE or register_date_to != BulkEmailForm.MAX_DATE:
        to_all = False
        dic.update({
            'date_joined__gte': timezone.datetime.strptime(register_date_from, BulkEmailForm.DATETIME_FORMAT),
            'date_joined__lte': timezone.datetime.strptime(register_date_to, BulkEmailForm.DATETIME_FORMAT) + timezone.timedelta(1,0,0),
        })

    # выбран ли конкретный платный/бесплатный вариант прохождения или тип сертификата
    # для фильтрации по EnrollmentReason
    paid = None
    if _check_enrollment_type_chosen():
        to_all = False
        if 'paid' in data['enrollment_type']:
            paid = True
        elif 'free' in data['enrollment_type']:
            paid = False
    elif len(data['got_certificate']) == 1:
        if 'paid' in data['got_certificate']:
            paid = True
        elif 'free' in data['got_certificate']:
            paid = False

    if paid is not None:
        paid_enr = list(EnrollmentReason.objects.filter(
            participant__session__id__in=session_ids,
            session_enrollment_type__mode='verified'
        ).values_list('participant__user__id', flat=True).distinct())
        if paid:
            dic.update({'id__in': paid_enr})
        else:
            dic_exclude.update({'id__in': paid_enr})
    if data['got_certificate']:
        # если не совпадает тип прохождения и платность полученного сертификата
        if len(data['enrollment_type']) == 1 and len(data['got_certificate']) == 1 and \
                data['enrollment_type'] != data['got_certificate']:
            return User.objects.none(), ''
        to_all = False
        have_cert = list(Participant.objects.filter(
            is_graduate=True,
            session__id__in=session_ids,
        ).values_list('user__id', flat=True))
        if 'id__in' in dic:
            dic['id__in'] = set(dic['id__in']).intersection(set(have_cert))
        else:
            dic['id__in'] = have_cert

    if 'id__in' in dic:
        dic.pop('participants__session__id__in', None)
    if subscription_ids is not None:
        # условия фильтрации пользователей по записям ИЛИ подписке на новости
        dic2 = dic.copy()
        dic2.pop('participants__session__id__in', None)
        dic2['id__in'] = subscription_ids
        if 'id__in' in dic or 'participants__session__id__in' in dic:
            users = User.objects.filter(Q(**dic) | Q(**dic2))
        else:
            users = User.objects.filter(**dic2)
    else:
        users = User.objects.filter(**dic)
    # т.к. все пользователи в plp пушатся активными, проверяем реальную активность в sso так
    users = users.exclude(**dic_exclude).exclude(last_name='').distinct()
    if data.get('instructors_filter'):
        q = Q(username__in=instructor_usernames)
        q = q if data['instructors_filter'] == 'only' else ~q
        users = users.filter(q)
    emails = set(users.values_list('email', flat=True))
    if data.get('subscribed'):
        emails = emails.union(subscribed_emails)
    return emails, 'to_all' if to_all else ''
