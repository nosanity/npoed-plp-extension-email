# coding: utf-8

import logging
import sys
import tempfile
from optparse import make_option
from django.core.management.base import BaseCommand
from post_office.lockfile import FileLock, FileLocked
from extension_email.notifications import send_queued


default_lockfile = tempfile.gettempdir() + "/support_email"


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('-L', '--lockfile', type='string', default=default_lockfile,
                    help='Absolute path of lockfile to acquire'),
    )

    def handle(self, *args, **options):
        try:
            with FileLock(options['lockfile']):
                try:
                    send_queued()
                except Exception as e:
                    logging.error(e, exc_info=sys.exc_info(), extra={'status_code': 500})
                    raise
        except FileLocked:
            logging.info('Failed to acquire lock, terminating now.')
