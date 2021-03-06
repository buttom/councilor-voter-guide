#! /usr/bin/env python
# -*- coding: utf-8 -*-
import sys
sys.path.append('../../')
import os
import re
import codecs
import unicodedata
import json
import glob
import psycopg2
import logging

import db_settings
import common
import vote_common


logging.basicConfig(filename='votes.log', level=logging.INFO)

def in_office_ids(date, exclude):
    if exclude:
        c.execute('''
            select id
            from councilors_councilorsdetail
            where election_year = %s and county = %s and term_start <= %s and cast(term_end::json->>'date' as date) > %s and id not in %s
        ''', (election_year, county, date, date, tuple(exclude)))
    else:
        c.execute('''
            select id
            from councilors_councilorsdetail
            where election_year = %s and county = %s and term_start <= %s and cast(term_end::json->>'date' as date) > %s
        ''', (election_year, county, date, date))
    return c.fetchall()

def UpsertVote(data):
    c.execute('''
        UPDATE votes_votes
        SET sitting_id = %(sitting_id)s, date = %(date)s, vote_seq = %(vote_seq)s, content = %(content)s, conflict = null
        WHERE uid = %(uid)s
    ''', data)
    c.execute('''
        INSERT INTO votes_votes(uid, sitting_id, date, vote_seq, content)
        SELECT %(uid)s, %(sitting_id)s, %(date)s, %(vote_seq)s, %(content)s
        WHERE NOT EXISTS (SELECT 1 FROM votes_votes WHERE uid = %(uid)s)
    ''', data)

def VoteVoterRelation(councilor_id, vote_id, decision):
    c.execute('''
        UPDATE votes_councilors_votes
        SET decision = %s, conflict = null
        WHERE councilor_id = %s AND vote_id = %s
    ''', (decision, councilor_id, vote_id))
    c.execute('''
        INSERT INTO votes_councilors_votes(councilor_id, vote_id, decision)
        SELECT %s, %s, %s
        WHERE NOT EXISTS (SELECT 1 FROM votes_councilors_votes WHERE councilor_id = %s AND vote_id = %s)
    ''',(councilor_id, vote_id, decision, councilor_id, vote_id))

def GetVoteContent(text):
    lines = [line.lstrip() for line in text.split('\n')]
    for i in reversed(range((0-len(lines)), -2)):
        if re.search(u'^議決', lines[i]):
            return '\n'.join(lines[i+1:])
        if re.search(u'(請.*審議|審議.*案)', lines[i]):
            return '\n'.join(lines[i:])
    for i in reversed(range((0-len(lines)), -1)):
        if re.search(u'^發言議員', lines[i]):
            return '\n'.join(lines[i-1:])
    for i in reversed(range((0-len(lines)), -1)):
        if re.search(u'(議員.*提議|其他事項$)', lines[i]):
            return '\n'.join(lines[i:])
    return lines[-1]


def IterVote(text, sitting_dict):
    text = re.sub(u'(議員)(計\s?\d+\s?位)', u'\g<1>：\g<2>', text)
    print sitting_dict["uid"]
    vote_count = 1
    pre_match_end = 0
    for match in Namelist_Token.finditer(text):
        vote_seq = str(vote_count).zfill(3)
        vote_dict = {'uid': '%s-%s' % (sitting_dict["uid"], vote_seq), 'sitting_id': sitting_dict["uid"], 'vote_seq': vote_seq, 'date': sitting_dict["date"], 'content': GetVoteContent(text[pre_match_end:match.end()])}
        print '=' * 20
        print vote_seq
        UpsertVote(vote_dict)
        ref = {'agree': 1, 'disagree': -1, 'abstain': 0}
        for key, value in ref.items():
            if match.group(key):
                names = re.sub(u'[、：，:,]', ' ', re.sub(u'\s', '', match.group(key)))
                for councilor_id in common.getCouncilorIdList(c, names):
                    id = common.getDetailIdFromUid(c, councilor_id, sitting_dict['election_year'], sitting_dict['county'])
                    VoteVoterRelation(id, vote_dict['uid'], value)
        vote_count += 1
        pre_match_end = match.end()

conn = db_settings.con()
c = conn.cursor()
election_years = {1: '2014', 2: '2018'}
county_abbr = os.path.dirname(os.path.realpath(__file__)).split('/')[-1]
county = common.county_abbr2string(county_abbr)
election_year = common.election_year(county)
county_abbr3 = common.county2abbr3(county)
total_text = unicodedata.normalize('NFC', codecs.open(u"../../../data/%s/meeting_minutes-%s.txt" % (county_abbr, election_year), "r", "utf-8").read())

Session_Token = re.compile(u'''
    \s*
    (?P<name>
        第\s*(?P<ad>[\d]+)\s*屆
        第\s*(?P<session>[\d]+)\s*次(?P<type>(定期|臨時))大?會
        \s*
        第\s*(?P<times>[\d]+)\s*次
        會議
    )
    \s*(?:會議)?紀錄
''', re.X)

Present_Token = re.compile(u'''
    出席[:：]?
    (?P<names>.+?)
    (?=(計\d+位|請假|列席))
''', re.X|re.S)

Namelist_Token = re.compile(u'''
    [:：]
    (?P<agree>[^:：]+?)
    [:：]
    (?P<disagree>[^:：]+?)
    [:：]
    (?P<abstain>[^:：]+?)
    [:：](通\s?過|否\s?決|同\s?意)
''', re.X|re.S)

sittings = []
for match in Session_Token.finditer(total_text):
    if match:
        if match.group('type') == u'定期':
            uid = '%s-%s-%02d-CS-%02d' % (county_abbr3, election_years[int(match.group('ad'))], int(match.group('session')), int(match.group('times')))
        elif match.group('type') == u'臨時':
            uid = '%s-%s-T%02d-CS-%02d' % (county_abbr3, election_years[int(match.group('ad'))], int(match.group('session')), int(match.group('times')))
        print uid
        sittings.append({
            "uid":uid,
            "name": re.sub('\s', '', match.group('name')),
            "county": county,
            "election_year": election_year,
            "session": match.group('session'),
            "date": common.ROC2AD(total_text[match.end():]),
            "start": match.start(), "end": match.end()
        })
for i in range(0, len(sittings)):
    # --> sittings, attendance, filelog
    if i != len(sittings)-1:
        one_sitting_text = total_text[sittings[i]['start']:sittings[i+1]['start']]
    else:
        one_sitting_text = total_text[sittings[i]['start']:]
    logging.info(sittings[i]['uid'])
    common.InsertSitting(c, sittings[i])
    common.FileLog(c, sittings[i]['name'])
    present_match = Present_Token.search(one_sitting_text)
    exclude = []
    if present_match:
        exclude.extend(common.Attendance(c, sittings[i], present_match.group('names'), 'CS', 'present'))
    # no councilor's name to record
    if exclude == []:
        continue
    # absent
    for councilor_id in in_office_ids(sittings[i]['date'], exclude):
        common.AddAttendanceRecord(c, councilor_id, sittings[i]['uid'], 'CS', 'absent')
    # <--
    # <--
    # --> votes
#   IterVote(one_sitting_text, sittings[i])
    # <--
conn.commit()
print 'votes, voter done!'

vote_common.not_attend_complement(c, county)
vote_common.person_attendance_param(c, county)
conn.commit()
print 'Succeed'
