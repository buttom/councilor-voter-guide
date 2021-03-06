# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-09-01 02:38
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('candidates', '0023_auto_20180812_0819'),
    ]

    operations = [
        migrations.AddField(
            model_name='terms',
            name='status',
            field=models.CharField(db_index=True, default='', max_length=100),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='terms',
            name='candidate',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='each_terms', to='candidates.Candidates', to_field=b'uid'),
        ),
    ]
