# -*- coding: utf-8 -*-


from django.db import models, migrations
import jsonfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('plp', '0001_squashed_0244_merge'),
        ('extension_email', '0002_bulkemailoptout'),
    ]

    operations = [
        migrations.CreateModel(
            name='CustomUnicodeCourseSession',
            fields=[
            ],
            options={
                'ordering': [],
                'proxy': True,
            },
            bases=('plp.coursesession',),
        ),
        migrations.AlterField(
            model_name='supportemail',
            name='target',
            field=jsonfield.fields.JSONField(null=True, blank=True),
        ),
    ]
