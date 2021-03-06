#! /usr/bin/env python
# -*- coding: utf-8 -*-
import sys
sys.path.append('../')
import os
import re
import json
import glob
import psycopg2
import pandas as pd

import db_settings
import common


def upsertCandidates(candidate):
    candidate['former_names'] = candidate.get('former_names', [])
    variants = common.make_variants_set(candidate['name'])
    candidate['identifiers'] = list((variants | set(candidate['former_names']) | {candidate['name'], re.sub(u'[\w‧]', '', candidate['name']), re.sub(u'\W', '', candidate['name']).lower(), }) - {''})
    c.execute('''
        SELECT district
        FROM councilors_councilorsdetail
        WHERE county = %(previous_county)s AND constituency = %(constituency)s
        ORDER BY election_year DESC
    ''', candidate)
    r = c.fetchone()
    if r:
        candidate['district'] = r[0]
    for district_change in district_versions[election_year].get(candidate['county'], []):
        if candidate['constituency'] == district_change['constituency']:
            candidate['district'] = district_change['district']
            candidate['constituency_change'] = district_change
            break
    complement = {'birth': None, 'gender': '', 'party': '', 'number': None, 'contact_details': None, 'district': '', 'education': None, 'experience': None, 'remark': None, 'image': '', 'links': None, 'platform': '', 'data': None}
    complement.update(candidate)
    c.execute('''
        INSERT INTO candidates_candidates(uid, name, birth, identifiers)
        VALUES (%(candidate_uid)s, %(name)s, %(birth)s, %(identifiers)s)
        ON CONFLICT (uid)
        DO UPDATE
        SET name = %(name)s, birth = %(birth)s, identifiers = %(identifiers)s
    ''', complement)
    c.execute('''
        INSERT INTO candidates_terms(uid, candidate_id, elected_councilor_id, councilor_terms, election_year, number, name, gender, party, constituency, county, district, contact_details, education, experience, remark, image, links, platform, type, status)
        VALUES (%(candidate_term_uid)s, %(candidate_uid)s, %(councilor_term_id)s, %(councilor_terms)s, %(election_year)s, %(number)s, %(name)s, %(gender)s, %(party)s, %(constituency)s, %(county)s, %(district)s, %(contact_details)s, %(education)s, %(experience)s, %(remark)s, %(image)s, %(links)s, %(platform)s, %(type)s, %(status)s)
        ON CONFLICT (election_year, candidate_id)
        DO UPDATE
        SET elected_councilor_id = %(councilor_term_id)s, councilor_terms = %(councilor_terms)s, number = %(number)s, name = %(name)s, gender = %(gender)s, party = %(party)s, constituency = %(constituency)s, county = %(county)s, district = %(district)s, contact_details = %(contact_details)s, education = %(education)s, experience = %(experience)s, remark = %(remark)s, image = %(image)s, links = %(links)s, status = %(status)s
    ''', complement)
    if complement.get('constituency_change'):
        c.execute('''
            UPDATE candidates_terms
            SET data = (COALESCE(data, '{}'::jsonb) || %s::jsonb)
            WHERE election_year = %s AND candidate_id = %s
        ''', (json.dumps({'constituency_change': complement['constituency_change']}), complement['election_year'], complement['candidate_uid']))
    terms = []
    for t in ['mayor', 'legislator', 'councilor']:
        if candidate.get('%s_terms' % t):
            for term in candidate['%s_terms' % t]:
                term['type'] = t
                terms.append(term)
    c.execute('''
        UPDATE candidates_terms
        SET data = (COALESCE(data, '{}'::jsonb) || %s::jsonb)
        WHERE election_year = %s and candidate_id = %s
    ''', [json.dumps({'terms': terms}), complement['election_year'], complement['candidate_uid'], ])

conn = db_settings.con()
c = conn.cursor()
election_year = '2014'
county_versions = json.load(open('../county_versions.json'))
district_versions = json.load(open('../district_versions.json'))
files = [f for f in glob.glob('../../data/candidates/%s/*.xlsx' % election_year)]
position_type = 'councilors'
path = '../../data/avatar/%s/%s' % (position_type, election_year)
for f in files:
    df = pd.read_excel(f, sheetname=0, names=['date', 'constituency', 'name', 'party'], usecols=[0, 1, 2, 3])
    df = df[df['name'] != u'姓名']
    candidates = json.loads(df.to_json(orient='records'))
    for candidate in candidates:
        candidate['type'] = 'councilors'
        candidate['status'] = 'approved'
        match = re.search(u'(?P<county>\W+)第(?P<num>\d+)選(?:舉)?區', candidate['constituency'])
        candidate['county'] = match.group('county') if match else None
        candidate['constituency'] = match.group('num') if match else None
        for county_change in county_versions[election_year]:
            candidate['previous_county'] = county_change['from'] if candidate['county'] == county_change['to'] else candidate['county']
        candidate['name'] = common.normalize_person_name(candidate['name'])
        candidate['name'] = re.sub(u'周鍾.*', u'周鍾㴴', candidate['name'])
        candidate['party'] = common.normalize_party(candidate['party'])
        candidate['election_year'] = election_year
        candidate['candidate_uid'], created = common.get_or_create_candidate_uid(c, candidate)
        candidate['candidate_term_uid'] = '%s-%s' % (candidate['candidate_uid'], election_year)
        candidate['councilor_uid'], created = common.get_or_create_councilor_uid(c, candidate, create=False)
        candidate['councilor_term_id'] = common.getDetailIdFromUid(c, candidate['councilor_uid'], election_year, candidate['county'])

        candidate['councilor_terms'] = common.councilor_terms(c, candidate) if created else None
        # image
        f_name = '%s_%d_%s' % (candidate['county'], int(candidate['constituency']), candidate['name'])
        f = '%s/%s' % (path, f_name)
        if os.path.isfile(f):
            candidate['image'] = u'%s/%s/%s/%s' % (common.storage_domain(), position_type, election_year, f_name)
        upsertCandidates(candidate)
conn.commit()
