"""
В целом копипаста post_office с единственным добавлением - отправкой сигнала после отправки пачки сообщений
Нужно из-за того, что теперь post_office апдейтит статус сообщений пачкой, а не использует метод save
"""
import tempfile
import sys
from multiprocessing import Pool
from multiprocessing.dummy import Pool as ThreadPool

from django.core.management.base import BaseCommand
from django.db import connection as db_connection
from django.db.models import Q
from django.utils.timezone import now

from post_office.connections import connections
from post_office.lockfile import FileLock, FileLocked
from post_office.logutils import setup_loghandlers
from post_office.mail import get_queued
from post_office.models import Email, Log, STATUS
from post_office.settings import get_log_level, get_threads_per_process
from post_office.utils import split_emails

from extension_email.models import emails_sent_signal

logger = setup_loghandlers()
default_lockfile = tempfile.gettempdir() + "/post_office"


def send_queued(processes=1, log_level=None):
    """
    Sends out all queued mails that has scheduled_time less than now or None
    """
    queued_emails = get_queued()
    total_sent, total_failed = 0, 0
    total_email = len(queued_emails)

    logger.info('Started sending %s emails with %s processes.' %
                (total_email, processes))

    if log_level is None:
        log_level = get_log_level()

    if queued_emails:

        # Don't use more processes than number of emails
        if total_email < processes:
            processes = total_email

        if processes == 1:
            total_sent, total_failed = _send_bulk(queued_emails,
                                                  uses_multiprocessing=False,
                                                  log_level=log_level)
        else:
            email_lists = split_emails(queued_emails, processes)

            pool = Pool(processes)
            results = pool.map(_send_bulk, email_lists)
            pool.terminate()

            total_sent = sum([result[0] for result in results])
            total_failed = sum([result[1] for result in results])
    message = '%s emails attempted, %s sent, %s failed' % (
        total_email,
        total_sent,
        total_failed
    )
    logger.info(message)
    return (total_sent, total_failed)


def _send_bulk(emails, uses_multiprocessing=True, log_level=None):
    # Multiprocessing does not play well with database connection
    # Fix: Close connections on forking process
    # https://groups.google.com/forum/#!topic/django-users/eCAIY9DAfG0
    if uses_multiprocessing:
        db_connection.close()

    if log_level is None:
        log_level = get_log_level()

    sent_emails = []
    failed_emails = []  # This is a list of two tuples (email, exception)
    email_count = len(emails)

    logger.info('Process started, sending %s emails' % email_count)

    def send(email):
        try:
            email.dispatch(log_level=log_level, commit=False,
                           disconnect_after_delivery=False)
            sent_emails.append(email)
            logger.debug('Successfully sent email #%d' % email.id)
        except Exception as e:
            logger.debug('Failed to send email #%d' % email.id)
            failed_emails.append((email, e))

    # Prepare emails before we send these to threads for sending
    # So we don't need to access the DB from within threads
    for email in emails:
        # Sometimes this can fail, for example when trying to render
        # email from a faulty Django template
        try:
            email.prepare_email_message()
        except Exception as e:
            failed_emails.append((email, e))

    number_of_threads = min(get_threads_per_process(), email_count)
    pool = ThreadPool(number_of_threads)

    pool.map(send, emails)
    pool.close()
    pool.join()

    connections.close()

    # Update statuses of sent and failed emails
    email_ids = [email.id for email in sent_emails]
    Email.objects.filter(id__in=email_ids).update(status=STATUS.sent)
    emails_sent_signal.send(None, status=STATUS.sent, ids=email_ids)

    email_ids = [email.id for (email, e) in failed_emails]
    Email.objects.filter(id__in=email_ids).update(status=STATUS.failed)
    emails_sent_signal.send(None, status=STATUS.failed, ids=email_ids)

    # If log level is 0, log nothing, 1 logs only sending failures
    # and 2 means log both successes and failures
    if log_level >= 1:

        logs = []
        for (email, exception) in failed_emails:
            logs.append(
                Log(email=email, status=STATUS.failed,
                    message=str(exception),
                    exception_type=type(exception).__name__)
            )

        if logs:
            Log.objects.bulk_create(logs)

    if log_level == 2:

        logs = []
        for email in sent_emails:
            logs.append(Log(email=email, status=STATUS.sent))

        if logs:
            Log.objects.bulk_create(logs)

    logger.info(
        'Process finished, %s attempted, %s sent, %s failed' % (
            email_count, len(sent_emails), len(failed_emails)
        )
    )

    return len(sent_emails), len(failed_emails)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            '-p', '--processes',
            type=int,
            default=1,
            help='Number of processes used to send emails',
        )
        parser.add_argument(
            '-L', '--lockfile',
            default=default_lockfile,
            help='Absolute path of lockfile to acquire',
        )
        parser.add_argument(
            '-l', '--log-level',
            type=int,
            help='"0" to log nothing, "1" to only log errors',
        )

    def handle(self, *args, **options):
        logger.info('Acquiring lock for sending queued emails at %s.lock' %
                    options['lockfile'])
        try:
            with FileLock(options['lockfile']):

                while 1:
                    try:
                        send_queued(options['processes'],
                                    options.get('log_level'))
                    except Exception as e:
                        logger.error(e, exc_info=sys.exc_info(),
                                     extra={'status_code': 500})
                        raise

                    # Close DB connection to avoid multiprocessing errors
                    db_connection.close()

                    if not Email.objects.filter(status=STATUS.queued) \
                            .filter(Q(scheduled_time__lte=now()) | Q(scheduled_time=None)).exists():
                        break
        except FileLocked:
            logger.info('Failed to acquire lock, terminating now.')
