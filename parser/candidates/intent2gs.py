#! /usr/bin/env python
# -*- coding: utf-8 -*-
import sys
sys.path.append('../')
import re
import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials

import db_settings
import common


conn = db_settings.con()
c = conn.cursor()
election_year = '2018'

scope = ['https://spreadsheets.google.com/feeds']
credentials = ServiceAccountCredentials.from_json_keyfile_name('credential.json', scope)
gc = gspread.authorize(credentials)
sh = gc.open_by_key('1URc-N8UnptWv0h7P1Aciar4NZgetWK7boVC6zrwQ3Iw')
wks = sh.sheet1

c.execute('''
    SELECT row_to_json(_)
    FROM (
        SELECT ci.name as user_input_name, ss.extra_data::json->'name' as fb_name, ci.type, ci.county, ci.constituency, ci.district, ci.party, ss.extra_data::json->'link' as fb_page_link, ci.uid
        FROM candidates_intent ci
        JOIN socialaccount_socialaccount ss ON ci.user_id = ss.user_id
        WHERE election_year = %s
        ORDER BY ci.id
    ) _
''', [election_year])
rows = c.fetchall()
headers = [(2, 'user_input_name'), (3, 'fb_name'), (4, 'type'), (5, 'county'), (6, 'constituency'), (7, 'district'), (8, 'party'), (9, 'fb_page_link'), (11, 'uid')]
wks.update_cell(1, 1, 'status')
for c, key in headers:
    wks.update_cell(1, c, key)
for r, row in enumerate(rows, start=2):
    row = row[0]
    if wks.cell(r, 1).value:
        continue
    for c, key in headers:
        wks.update_cell(r, c, row[key])
