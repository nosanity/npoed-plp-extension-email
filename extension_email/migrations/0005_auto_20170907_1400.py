# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('post_office', '0004_auto_20161111_1752'),
        ('extension_email', '0004_supportemailtemplate'),
    ]

    operations = [
        migrations.CreateModel(
            name='EmailRelated',
            fields=[
                ('email_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='post_office.Email')),
                ('mass_mail_id', models.PositiveIntegerField()),
            ],
            bases=('post_office.email',),
        ),
        migrations.AddField(
            model_name='supportemail',
            name='delivered_number',
            field=models.PositiveIntegerField(default=0, verbose_name='\u0414\u043e\u0441\u0442\u0430\u0432\u043b\u0435\u043d\u043e \u043f\u0438\u0441\u0435\u043c'),
        ),
        migrations.AddField(
            model_name='supportemail',
            name='recipients_number',
            field=models.PositiveIntegerField(default=0, verbose_name='\u041a\u043e\u043b\u0438\u0447\u0435\u0441\u0442\u0432\u043e \u043f\u043e\u043b\u0443\u0447\u0430\u0442\u0435\u043b\u0435\u0439'),
        ),
        migrations.AddField(
            model_name='supportemail',
            name='unsubscriptions',
            field=models.PositiveIntegerField(default=0, verbose_name='\u041a\u043e\u043b\u0438\u0447\u0435\u0441\u0442\u0432\u043e \u043e\u0442\u043f\u0438\u0441\u0430\u0432\u0448\u0438\u0445\u0441\u044f'),
        ),
    ]
