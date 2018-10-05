# -*- coding: utf-8 -*-

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('extension_email', '0006_auto_20170927_1421'),
    ]

    operations = [
        migrations.CreateModel(
            name='SupportEmailStatus',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('email', models.EmailField(max_length=254, db_index=True)),
                ('status', models.SmallIntegerField(default=2, choices=[(0, 'sent'), (1, 'failed'), (2, 'queued')])),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('support_email', models.ForeignKey(to='extension_email.SupportEmail', on_delete=models.CASCADE)),
            ],
        ),
    ]
