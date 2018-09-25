# -*- coding: utf-8 -*-


from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('extension_email', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='BulkEmailOptout',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='\u041a\u043e\u0433\u0434\u0430 \u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u044c \u043e\u0442\u043f\u0438\u0441\u0430\u043b\u0441\u044f \u043e\u0442 \u0440\u0430\u0441\u0441\u044b\u043b\u043a\u0438')),
                ('user', models.ForeignKey(related_name='bulk_email_optout', verbose_name='\u041f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u044c', to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE)),
            ],
            options={
                'verbose_name': '\u041e\u0442\u043f\u0438\u0441\u043a\u0430 \u043e\u0442 \u0440\u0430\u0441\u0441\u044b\u043b\u043e\u043a',
                'verbose_name_plural': '\u041e\u0442\u043f\u0438\u0441\u043a\u0438 \u043e\u0442 \u0440\u0430\u0441\u0441\u044b\u043b\u043e\u043a',
            },
        ),
    ]
