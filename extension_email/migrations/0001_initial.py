# -*- coding: utf-8 -*-


from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='SupportEmail',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('target', models.CharField(default=b'myself', max_length=15, verbose_name='\u0424\u0438\u043b\u044c\u0442\u0440', choices=[(b'myself', '\u0421\u0435\u0431\u0435'), (b'everyone', '\u0412\u0441\u0435\u043c')])),
                ('subject', models.CharField(max_length=128, verbose_name='\u0422\u0435\u043c\u0430', blank=True)),
                ('html_message', models.TextField(null=True, verbose_name='HTML \u043f\u0438\u0441\u044c\u043c\u0430', blank=True)),
                ('text_message', models.TextField(null=True, verbose_name='\u0422\u0435\u043a\u0441\u0442 \u043f\u0438\u0441\u044c\u043c\u0430', blank=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('sender', models.ForeignKey(verbose_name='\u041e\u0442\u043f\u0440\u0430\u0432\u0438\u0442\u0435\u043b\u044c', to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE)),
            ],
            options={
                'verbose_name': '\u0420\u0430\u0441\u0441\u044b\u043b\u043a\u0430',
                'verbose_name_plural': '\u0420\u0430\u0441\u0441\u044b\u043b\u043a\u0438',
            },
        ),
    ]
