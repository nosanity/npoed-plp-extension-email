# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('extension_email', '0003_auto_20161003_1739'),
    ]

    operations = [
        migrations.CreateModel(
            name='SupportEmailTemplate',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('slug', models.CharField(unique=True, max_length=128, verbose_name='\u041d\u0430\u0437\u0432\u0430\u043d\u0438\u0435 \u0448\u0430\u0431\u043b\u043e\u043d\u0430')),
                ('subject', models.CharField(max_length=128, verbose_name='\u0422\u0435\u043c\u0430')),
                ('html_message', models.TextField(verbose_name='HTML \u043f\u0438\u0441\u044c\u043c\u0430')),
                ('text_message', models.TextField(null=True, verbose_name='\u0422\u0435\u043a\u0441\u0442 \u043f\u0438\u0441\u044c\u043c\u0430', blank=True)),
            ],
            options={
                'verbose_name': '\u0428\u0430\u0431\u043b\u043e\u043d \u0440\u0430\u0441\u0441\u044b\u043b\u043a\u0438',
                'verbose_name_plural': '\u0428\u0430\u0431\u043b\u043e\u043d\u044b \u0440\u0430\u0441\u0441\u044b\u043b\u043e\u043a',
            },
        ),
    ]
