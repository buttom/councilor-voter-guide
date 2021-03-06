# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2017-07-17 08:18
from __future__ import unicode_literals

import django.contrib.postgres.fields.jsonb
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('councilors', '0005_auto_20170322_1055'),
    ]

    operations = [
        migrations.CreateModel(
            name='Bills',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uid', models.TextField(db_index=True, unique=True)),
                ('election_year', models.CharField(db_index=True, max_length=100)),
                ('county', models.CharField(db_index=True, max_length=100)),
                ('type', models.TextField(blank=True, null=True)),
                ('category', models.TextField(blank=True, null=True)),
                ('abstract', models.TextField(blank=True, null=True)),
                ('description', models.TextField(blank=True, null=True)),
                ('methods', models.TextField(blank=True, null=True)),
                ('last_action', models.TextField(blank=True, null=True)),
                ('proposed_by', models.TextField(blank=True, null=True)),
                ('petitioned_by', models.TextField(blank=True, null=True)),
                ('brought_by', models.TextField(blank=True, null=True)),
                ('related_units', models.TextField(blank=True, null=True)),
                ('committee', models.TextField(blank=True, null=True)),
                ('bill_no', models.TextField(blank=True, null=True)),
                ('execution', models.TextField(blank=True, null=True)),
                ('motions', django.contrib.postgres.fields.jsonb.JSONField(null=True)),
                ('remark', models.TextField(blank=True, null=True)),
                ('links', models.TextField(blank=True, null=True)),
                ('param', django.contrib.postgres.fields.jsonb.JSONField(null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Councilors_Bills',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('priproposer', models.NullBooleanField()),
                ('petition', models.NullBooleanField()),
                ('bill', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='bills.Bills', to_field=b'uid')),
                ('councilor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='councilors.CouncilorsDetail')),
            ],
        ),
        migrations.AddField(
            model_name='bills',
            name='proposer',
            field=models.ManyToManyField(blank=True, db_index=True, null=True, through='bills.Councilors_Bills', to='councilors.CouncilorsDetail'),
        ),
    ]
