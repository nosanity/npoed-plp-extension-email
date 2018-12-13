# coding: utf-8

import logging
import sys
import tempfile
from django.core.management.base import BaseCommand
from post_office.lockfile import FileLock, FileLocked
from extension_email.notifications import send_queued


default_lockfile = tempfile.gettempdir() + "/support_email"


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            '-L', '--lockfile',
            type=str,
            default=default_lockfile,
            help='Absolute path of lockfile to acquire'
        )

    def handle(self, *args, **options):
        try:
            with FileLock(options['lockfile']):
                try:
                    send_queued()
                except Exception as e:
                    logging.error(e, exc_info=sys.exc_info(), extra={'status_code': 500})
        except FileLocked:
            logging.info('Failed to acquire lock, terminating now.')
