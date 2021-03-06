# -*- coding: utf-8 -*-
from django.db import models
from django.contrib.postgres.fields import JSONField


class Bills(models.Model):
    proposer = models.ManyToManyField('councilors.CouncilorsDetail', blank=True, null=True, through='Councilors_Bills', db_index=True)
    uid = models.TextField(unique=True, db_index=True)
    election_year = models.CharField(max_length=100, db_index=True)
    county = models.CharField(max_length=100, db_index=True)
    type = models.TextField(blank=True, null=True)
    category = models.TextField(blank=True, null=True)
    abstract = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    methods = models.TextField(blank=True, null=True)
    last_action = models.TextField(blank=True, null=True)
    proposed_by = models.TextField(blank=True, null=True)
    petitioned_by = models.TextField(blank=True, null=True)
    brought_by = models.TextField(blank=True, null=True)
    related_units = models.TextField(blank=True, null=True)
    committee = models.TextField(blank=True, null=True)
    bill_no = models.TextField(blank=True, null=True)
    execution = models.TextField(blank=True, null=True)
    motions = JSONField(null=True)
    remark = models.TextField(blank=True, null=True)
    link = models.TextField(blank=True, null=True)
    links = JSONField(null=True)
    param = JSONField(null=True)
    def __unicode__(self):
        return self.uid

class Councilors_Bills(models.Model):
    councilor = models.ForeignKey('councilors.CouncilorsDetail', blank=True, null=True)
    bill = models.ForeignKey(Bills, to_field='uid')
    priproposer = models.NullBooleanField()
    petition = models.NullBooleanField()
    class Meta:
        unique_together = ('councilor', 'bill')

class Mayors_Bills(models.Model):
    mayor = models.ForeignKey('mayors.terms', to_field='uid')
    bill = models.ForeignKey(Bills, to_field='uid')
    class Meta:
        unique_together = ('mayor', 'bill')
