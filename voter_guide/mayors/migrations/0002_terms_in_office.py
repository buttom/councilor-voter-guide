# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-05-10 08:15
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mayors', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='terms',
            name='in_office',
            field=models.BooleanField(db_index=True, default=True),
            preserve_default=False,
        ),
    ]
