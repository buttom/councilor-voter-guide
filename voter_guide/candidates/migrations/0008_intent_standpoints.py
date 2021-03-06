# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-01-17 12:05
from __future__ import unicode_literals

import django.contrib.postgres.fields.jsonb
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('suggestions', '0005_suggestions_suggestor_name'),
        ('bills', '0004_auto_20170718_0437'),
        ('votes', '0002_auto_20170718_0438'),
        ('candidates', '0007_intent_likes_create_at'),
    ]

    operations = [
        migrations.CreateModel(
            name='Intent_Standpoints',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('pro', models.BooleanField(db_index=True, verbose_name='\u8d0a\u6210')),
                ('comment', models.TextField(blank=True, null=True, verbose_name='\u610f\u898b')),
                ('create_at', models.DateTimeField(auto_now_add=True)),
                ('data', django.contrib.postgres.fields.jsonb.JSONField(null=True)),
                ('bill', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='intent_standpoints', to='bills.Bills', to_field=b'uid')),
                ('intent', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='candidates.Intent', to_field=b'uid')),
                ('suggestion', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='intent_standpoints', to='suggestions.Suggestions', to_field=b'uid')),
                ('vote', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='intent_standpoints', to='votes.Votes', to_field=b'uid')),
            ],
        ),
    ]
