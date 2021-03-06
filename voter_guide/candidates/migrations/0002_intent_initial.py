# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2017-05-26 12:45
from __future__ import unicode_literals

from django.conf import settings
import django.contrib.postgres.fields.jsonb
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('candidates', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Intent',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uid', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('councilor_terms', django.contrib.postgres.fields.jsonb.JSONField(null=True)),
                ('election_year', models.CharField(db_index=True, default=b'2018', max_length=4)),
                ('likes', models.IntegerField(db_index=True, default=0)),
                ('name', models.CharField(max_length=100, verbose_name='\u59d3\u540d')),
                ('gender', models.CharField(blank=True, max_length=100, null=True, verbose_name='\u6027\u5225')),
                ('party', models.CharField(db_index=True, max_length=100, verbose_name='\u653f\u9ee8')),
                ('constituency', models.PositiveIntegerField(db_index=True, verbose_name='\u9078\u8209\u5340')),
                ('county', models.CharField(db_index=True, max_length=100, verbose_name='\u7e23\u5e02')),
                ('district', models.CharField(blank=True, db_index=True, max_length=100, null=True)),
                ('contact_details', django.contrib.postgres.fields.jsonb.JSONField(null=True)),
                ('education', models.TextField(blank=True, null=True, verbose_name='\u5b78\u6b77')),
                ('experience', models.TextField(blank=True, null=True, verbose_name='\u7d93\u6b77')),
                ('remark', models.TextField(blank=True, null=True, verbose_name='\u5099\u8a3b')),
                ('links', django.contrib.postgres.fields.jsonb.JSONField(null=True)),
                ('motivation', models.TextField(blank=True, null=True, verbose_name='\u70ba\u4ec0\u9ebc\u8981\u9078')),
                ('platform', models.TextField(blank=True, null=True, verbose_name='\u653f\u898b')),
                ('politicalcontributions', django.contrib.postgres.fields.jsonb.JSONField(null=True)),
                ('status', models.CharField(db_index=True, max_length=100)),
                ('history', django.contrib.postgres.fields.jsonb.JSONField(null=True)),
                ('candidate', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='candidates.Candidates', to_field=b'uid')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='intent',
            unique_together=set([('user', 'election_year')]),
        ),
        migrations.AlterIndexTogether(
            name='intent',
            index_together=set([('election_year', 'county', 'constituency')]),
        ),
    ]
