#! /usr/bin/env python
# -*- coding: utf-8 -*-
import sys
sys.path.append('../')
import re
import glob
import json
import codecs
import subprocess
from pandas import *
import pandas as pd
from numpy import nan
import logging
import ast
from sys import argv

import common
import db_settings


logging.basicConfig(filename='suggestions_parser.log', level=logging.INFO)

def is_number(text):
    try:
        float(text)
        return True
    except:
        return False

def get_election_year(county, suggest_year):
    c.execute('''
        SELECT election_year
        FROM councilors_councilorsdetail
        WHERE county = %s
        GROUP BY election_year
        ORDER BY election_year desc
    ''', (county,))
    r = c.fetchall()
    for election_year in r:
        if int(suggest_year) > int(election_year[0]):
            return election_year[0]

def getCouncilordetailIdList(id_list, election_year, county):
    if id_list:
        c.execute('''
            SELECT id
            FROM councilors_councilorsdetail
            WHERE councilor_id IN %s and election_year = %s and county = %s
        ''', (tuple(id_list), election_year, county))
        r = c.fetchall()
        if r:
            return [x[0] for x in r]
        for id in id_list:
            logging.error("Can't find this counculor at this year : %s, %s, %s" % (election_year, county, id))
#           raw_input()

def normalize_person_name(name):
    name = re.sub(u'(副?議長|議員)[.]', '\n', name)
    name = re.sub(u'[。˙・･•．.]', u'‧', name)
    name = re.sub(u' {3}', '\n', name)
    name = re.sub(u'[　()（） ]', '', name)
    name = re.sub(u'(副?議長|議員)', '', name)
    name = re.sub(u'[、/;]', '\n', name)
    if len(name) > 5:
        name = re.sub(u'(\W+)和(\W+)', u'\g<1>\n\g<2>', name)
#   for wrong, right in [(u'游輝', u'游輝宂'), (u'連婓璠', u'連斐璠'), (u'羅文幟', u'羅文熾'), (u'郭昭嚴', u'郭昭巖'), (u'闕梅莎', u'闕枚莎'), (u'林亦華', u'林奕華'), (u'周鍾$', u'周鍾㴴'), (u'汪志銘', u'汪志冰'), (u'簡余宴', u'簡余晏'), (u'周佑威', u'周威佑'), (u'黃洋', u'黃平洋'), (u'周玲玟', u'周玲妏')]:
#       name = re.sub(wrong, right, name)
    name = name.title()
    return name

def sheet2df(target_sheet=0):
    df = pd.read_excel(f, sheetname=target_sheet, header=None, encoding='utf-8')
    no_person_name = False
    if not re.search(u'(姓名|名稱)', df.iloc[3:5, 0].to_string(na_rep='', index=False)):
        header_label = df.iloc[3:5, 8].to_string(na_rep='', index=False).strip()
        if len(df.columns) > 8 and (header_label == '' or header_label == u'單位'):
            should_drop_column = 8
        else:
            should_drop_column = 0
        no_person_name = True
    election_year = get_election_year(county, meta['year'])
    if len(df.columns) < 9:
        logging.info('no name column!!')
        df = pd.read_excel(f, sheetname=target_sheet, header=None, usecols=range(0, 8), skiprows=5, names=['suggestion', 'position', 'suggest_expense', 'approved_expense', 'expend_on', 'brought_by', 'bid_type', 'bid_by'], encoding='utf-8')
        df.dropna(inplace=True, how='any', subset=['suggestion', 'position', 'approved_expense'])
        for key in ['position', 'suggest_expense', 'brought_by', ]:
            df[key].fillna(inplace=True, method='pad')
        df['councilor_num'] = 1
        df['suggestor_name'] = nan
    else:
        if no_person_name:
            if should_drop_column == 0:
                df = pd.read_excel(f, sheetname=target_sheet, header=None, usecols=range(1, 9), skiprows=5, names=['suggestion', 'position', 'suggest_expense', 'approved_expense', 'expend_on', 'brought_by', 'bid_type', 'bid_by'], encoding='utf-8')
            elif should_drop_column == 8:
                df = pd.read_excel(f, sheetname=target_sheet, header=None, usecols=range(0, 8), skiprows=5, names=['suggestion', 'position', 'suggest_expense', 'approved_expense', 'expend_on', 'brought_by', 'bid_type', 'bid_by'], encoding='utf-8')
            df.dropna(inplace=True, how='any', subset=['suggestion', 'position', 'approved_expense'])
            for key in ['position', 'suggest_expense', 'brought_by', ]:
                df[key].fillna(inplace=True, method='pad')
            df['councilor_num'] = 1
            df['suggestor_name'] = nan
        else:
            df = pd.read_excel(f, sheetname=target_sheet, header=None, usecols=range(0, 9), skiprows=5, names=['councilor', 'suggestion', 'position', 'suggest_expense', 'approved_expense', 'expend_on', 'brought_by', 'bid_type', 'bid_by'], encoding='utf-8')
            df.dropna(inplace=True, how='any', subset=['suggestion', 'position', 'approved_expense'])
            for key in ['councilor', 'suggestion', 'position', 'suggest_expense', 'brought_by', 'bid_type', 'bid_by']:
                df[key].fillna(inplace=True, method='pad')
            df['suggestor_name'] = df['councilor']
            df['councilor'] = map(lambda x: normalize_person_name(x) if x else nan, df['councilor'])
            df['councilor_ids'] = map(lambda x: getCouncilordetailIdList(common.getCouncilorIdList(c, x), election_year, county) if x else nan, df['councilor'])
            df['councilor_num'] = map(lambda x: len(x) if x else 1, df['councilor_ids'])
    df['election_year'] = election_year
    df['county'] = county
    df['suggest_year'] = meta['year']
    df['suggest_month'] = meta['month_to']
    df['uid'] = map(lambda x: u'{county}-{year}-{month_from}-{month_to}'.format(**meta) + '-%d' % (x+6), df.index)
    df['approved_expense'] = map(lambda x: float(x) if is_number(x) else nan, df['approved_expense'])
    df['suggest_expense'] = map(lambda x: float(x) if is_number(x) else nan, df['suggest_expense'])
    if df['approved_expense'].mean() < 5000.0:
        df['approved_expense'] = map(lambda x: x*1000 if is_number(x) else nan, df['approved_expense'])
        df['suggest_expense'] = map(lambda x: x*1000 if is_number(x) else nan, df['suggest_expense'])
    df['approved_expense_avg'] = df['approved_expense'] / df['councilor_num']
    df['suggest_expense_avg'] = df['suggest_expense'] / df['councilor_num']
    return df

year = 2017
conn = db_settings.con()
c = conn.cursor()
if len(argv) > 1:
    target_county = ast.literal_eval(argv[1])['county']
else:
    target_county = '*'
county_config = json.load(open('county_config.json'))
df_concat = DataFrame()
for meta_file in glob.glob('../../data/%s/suggestions.json' % target_county):
    county_abbr = meta_file.split('/')[-2]
    county = common.county_abbr2string(county_abbr)
    with open(meta_file) as meta_file:
        metas = json.load(meta_file)
        exclude_ods_metas = []
        for meta in metas:
            exclude_ods_metas.append({x: meta[x] for x in ["month_to", "year", "month_from"] if meta['file_ext'] != 'ods'})
        for meta in metas:
            if meta['file_ext'] == 'pdf' or meta['year'] != year:
                continue
            meta['county'] = county
            file_name = '{year}_{month_from}-{month_to}.{file_ext}'.format(**meta)
            logging.info('%s %s' % (county, file_name))
            f = '../../data/%s/suggestions/%s' % (county_abbr, file_name)
            if {x: meta[x] for x in ["month_to", "year", "month_from"]} in county_config.get(county_abbr, {}).get('duplicated_reports', []):
                logging.info('pass %s %s' % (county, file_name))
                continue
            if county_config.get(county_abbr, {}).get('redirect'):
                for file_from, file_to in county_config[county_abbr]['redirect'].items():
                    if file_name == file_from:
                        file_name = file_to
                        f = '../../data/%s/suggestions/%s' % (county_abbr, file_name)
                        logging.info('redirect to %s %s' % (county, file_name))
                        break
            if not re.search('xls', meta['file_ext']):
                # if this file are ods only
                if meta['file_ext'] == 'ods' and {x: meta[x] for x in ["month_to", "year", "month_from"]} not in exclude_ods_metas:
                    cmd = 'unoconv -d spreadsheet --format=xls %s' % f
                    subprocess.call(cmd, shell=True)
                    meta['file_ext'] = 'xls'
                    file_name = '{year}_{month_from}-{month_to}.{file_ext}'.format(**meta)
                    logging.info('convert to: %s' % file_name)
                    f = '../../data/%s/suggestions/%s' % (county_abbr, file_name)
                else:
                    logging.info('pass %s %s' % (county, file_name))
                    continue
            try:
                target_sheet = county_config.get(county_abbr, {}).get('target_sheet').get('{year}_{month_from}-{month_to}'.format(**meta), 0)
            except:
                target_sheet = county_config.get(county_abbr, {}).get('target_sheet', 0)
            if target_sheet == 0:
                df = sheet2df()
            elif target_sheet == 'all':
                xl = pd.ExcelFile(f)
                for sheet_name in xl.sheet_names:
                    if re.search(u'上半年', sheet_name):
                        meta['month_from'] = '01'
                        meta['month_to'] = '06'
                        logging.info('%s %s' % (meta['year'], meta['month_to']))
                        df = sheet2df(sheet_name)
                    else:
                        meta['month_from'] = '07'
                        meta['month_to'] = '12'
                        logging.info('%s %s' % (meta['year'], meta['month_to']))
                        df = sheet2df(sheet_name)
                    df_concat = concat([df_concat, df])
            elif target_sheet == 'second_half_year':
                xl = pd.ExcelFile(f)
                for sheet_name in xl.sheet_names:
                    if re.search(u'\.12', sheet_name):
                        meta['year'] = int(sheet_name.split('.')[0]) + 1911
                        meta['month_from'] = '01'
                        meta['month_to'] = '12'
                        logging.info('%s %s' % (meta['year'], meta['month_to']))
                        df = sheet2df(sheet_name)
                        df_concat = concat([df_concat, df])
            else:
                xl = pd.ExcelFile(f)
                for sheet_name in xl.sheet_names:
                    if re.search(target_sheet, sheet_name):
                        df = sheet2df(sheet_name)
                        df_concat = concat([df_concat, df])
            df_concat = concat([df_concat, df])

def Suggestions(suggestion):
    for column in ['position', 'expend_on', 'brought_by', 'bid_type', 'bid_by']:
        try:
            suggestion[column] = suggestion[column].strip() if suggestion[column] else ''
        except:
            logging.critical('%s, %s, %s' % (suggestion['uid'], column, suggestion[column]))
            raise
    suggestion['bid_by'] = re.sub(u'[\d.,、]', ' ', suggestion['bid_by'])
    suggestion['bid_by'] = [x.strip() for x in suggestion['bid_by'].split() if x.strip()]
    c.execute('''
        INSERT INTO suggestions_suggestions(uid, county, election_year, suggest_year, suggest_month, suggestor_name, suggestion, position, suggest_expense, suggest_expense_avg, approved_expense, approved_expense_avg, expend_on, brought_by, bid_type, bid_by, district, constituency)
        VALUES (%(uid)s, %(county)s, %(election_year)s, %(suggest_year)s, %(suggest_month)s, %(suggestor_name)s, %(suggestion)s, %(position)s, %(suggest_expense)s, %(suggest_expense_avg)s, %(approved_expense)s, %(approved_expense_avg)s, %(expend_on)s, %(brought_by)s, %(bid_type)s, %(bid_by)s, %(district)s, %(constituency)s)
        ON CONFLICT (uid)
        DO UPDATE
        SET county = %(county)s, election_year = %(election_year)s, suggest_year = %(suggest_year)s, suggest_month = %(suggest_month)s, suggestor_name = %(suggestor_name)s, suggestion = %(suggestion)s, position = %(position)s, suggest_expense = %(suggest_expense)s, suggest_expense_avg = %(suggest_expense_avg)s, approved_expense_avg = %(approved_expense_avg)s, approved_expense = %(approved_expense)s, expend_on = %(expend_on)s, brought_by = %(brought_by)s, bid_type = %(bid_type)s, bid_by = %(bid_by)s, district = %(district)s, constituency = %(constituency)s
    ''', suggestion)

def CouncilorsSuggestions(suggestion):
    c.execute('''
        INSERT INTO suggestions_councilors_suggestions(councilor_id, suggestion_id, jurisdiction)
        VALUES (%(councilor_id)s, %(uid)s, %(jurisdiction)s)
        ON CONFLICT (councilor_id, suggestion_id)
        DO UPDATE
        SET jurisdiction = %(jurisdiction)s
    ''', suggestion)

def get_district(text, suggestion):
    if not text:
        return None, None
    for councilor_id in item['councilor_ids']:
        c.execute('''
            SELECT constituency, district
            FROM councilors_councilorsdetail
            WHERE id = %s AND district != ''
        ''', (councilor_id, ))
        r = c.fetchall()
        for constituency, district in r:
            for region in district.decode('utf-8').split(u'、'):
                if text.find(region) != -1:
                    return int(constituency), region
    c.execute('''
        SELECT constituency, district
        FROM councilors_councilorsdetail
        WHERE county = %(county)s AND election_year = %(election_year)s AND district != ''
        GROUP BY constituency, district
        ORDER BY constituency, district
    ''', suggestion)
    r = c.fetchall()
    for constituency, district in r:
        for region in district.decode('utf-8').split(u'、'):
            if text.find(region) != -1:
                return int(constituency), region
    return None, None

def get_jurisdiction(suggestion):
    c.execute('''
        SELECT *
        FROM councilors_councilorsdetail
        WHERE id = %(councilor_id)s AND constituency = %(constituency)s
    ''', suggestion)
    r = c.fetchall()
    return True if r else False

ds = df_concat.to_json(orient='records', force_ascii=False)
dict_list = json.loads(ds)
for item in dict_list:
    if item.get('councilor_ids'):
        for column in ['position', 'suggestion', 'brought_by']:
            item['constituency'], item['district'] = get_district(item[column], item)
            if item['constituency']:
                break
    else:
        item['constituency'], item['district'] =  None, None
    Suggestions(item)
    if item.get('councilor_ids'):
        for councilor_id in item['councilor_ids']:
            item['councilor_id'] = councilor_id
            item['jurisdiction'] = get_jurisdiction(item) if item['constituency'] else None
            CouncilorsSuggestions(item)
conn.commit()

# update suggestions params on councilor
def one_councilor_term_years(data):
    c.execute('''
        SELECT json_build_object('sum', SUM(_.sum), 'count', SUM(_.count), 'years', json_agg(_))
        FROM (
            SELECT suggest_year, COALESCE(SUM(approved_expense_avg), 0) as sum, COALESCE(COUNT(*), 0) as count, SUM(
                CASE
                    WHEN approved_expense <= 100000 THEN 1 ELSE 0
                END
            ) as small_purchase
            FROM suggestions_suggestions s, suggestions_councilors_suggestions sc
            WHERE s.uid = sc.suggestion_id AND sc.councilor_id = %(councilor_id)s
            GROUP BY suggest_year
            ORDER BY suggest_year
        ) _
    ''', data)
    return c.fetchone()[0]

def one_pile_json(data):
    c.execute('''
        SELECT json_build_object('label', %(label)s, 'tokens', %(tokens)s, 'sum', COALESCE(SUM(approved_expense_avg), 0), 'count', COALESCE(COUNT(*), 0))
        FROM suggestions_suggestions s, suggestions_councilors_suggestions sc
        WHERE s.uid = sc.suggestion_id AND sc.councilor_id = %(councilor_id)s AND (suggestion ~* %(tokens)s OR position ~* %(tokens)s OR brought_by ~* %(tokens)s)
    ''', data)
    return c.fetchone()[0]

def one_association_json(token):
    c.execute('''
        SELECT json_build_object('label', %(label)s, 'sum', COALESCE(SUM(approved_expense_avg), 0), 'count', COALESCE(COUNT(*), 0))
        FROM suggestions_suggestions s, suggestions_councilors_suggestions sc
        WHERE s.uid = sc.suggestion_id AND sc.councilor_id = %(councilor_id)s AND (suggestion ~* %(label)s OR position ~* %(label)s OR brought_by ~* %(label)s)
    ''', data)
    return c.fetchone()[0]

c.execute('''
    SELECT councilor_id
    FROM suggestions_councilors_suggestions
    GROUP BY councilor_id
''')
for councilor_id in c.fetchall():
    piles = []
    for pile, tokens in [(u'協會', [u'協會', u'學會', u'商會', u'公會', u'協進會', u'促進會', u'研習會', u'婦聯會', u'婦女會', u'體育會', u'同心會', u'農會', u'早起會', u'健身會', u'宗親會', u'功德會', u'商業會', u'長青會', u'民眾服務社', u'聯盟']), (u'辦公室', [u'辦公室', u'辦公處']), (u'廟', [u'廟', u'宮']), (u'警察局', [u'警察局', u'分局']), (u'消防局', [u'消防局', u'消防隊', u'分隊', u'中隊']), (u'國中、國小', [u'國中', u'國小', u'中學', u'小學'])]:
        data = {
            'councilor_id': councilor_id,
            'label': pile,
            'tokens': u'%s' % u'|'.join(tokens)
        }
        r = one_pile_json(data)
        if r['sum']:
            piles.append(r)
    piles = sorted(piles, key=lambda x: x['sum'], reverse=True)
    c.execute('''
        UPDATE councilors_councilorsdetail
        SET param = (COALESCE(param, '{}'::jsonb) || %s::jsonb)
        WHERE id = %s
    ''', (json.dumps({'suggestions_piles': piles}), councilor_id))
    c.execute('''
        UPDATE councilors_councilorsdetail
        SET param = (COALESCE(param, '{}'::jsonb) || %s::jsonb)
        WHERE id = %s
    ''', (json.dumps({'suggestions_years': one_councilor_term_years(data)}), councilor_id))
    associations = []
    for token in [u'社區發展協會', u'學會', u'商會', u'公會', u'協進會', u'促進會', u'研習會', u'婦聯會', u'婦女會', u'體育會', u'同心會', u'農會', u'早起會', u'健身會', u'宗親會', u'功德會', u'商業會', u'長青會', u'民眾服務社', u'聯盟']:
        data = {
            'councilor_id': councilor_id,
            'label': token
        }
        r = one_association_json(token)
        if r['sum']:
            associations.append(r)
    associations = sorted(associations, key=lambda x: x['sum'], reverse=True)
    c.execute('''
        UPDATE councilors_councilorsdetail
        SET param = (COALESCE(param, '{}'::jsonb) || %s::jsonb)
        WHERE id = %s
    ''', (json.dumps({'suggestions_associations': associations}), councilor_id))
conn.commit()

# update suggestions params on mayor
def one_mayor_term_years(data):
    c.execute('''
        SELECT json_build_object('sum', SUM(_.sum), 'count', SUM(_.count), 'years', json_agg(_))
        FROM (
            SELECT suggest_year, COALESCE(SUM(approved_expense_avg), 0) as sum, COALESCE(COUNT(*), 0) as count, SUM            (
                CASE
                    WHEN approved_expense <= 100000 THEN 1 ELSE 0
                END
            ) as small_purchase
            FROM suggestions_suggestions s
            WHERE county = %(county)s AND election_year = %(election_year)s
            GROUP BY suggest_year
            ORDER BY suggest_year
        ) _
    ''', data)
    return c.fetchone()[0]

def one_mayor_pile_json(data):
    c.execute('''
        SELECT json_build_object('label', %(label)s, 'tokens', %(tokens)s, 'sum', COALESCE(SUM(approved_expense_avg), 0), 'count', COALESCE(COUNT(*), 0))
        FROM suggestions_suggestions
        WHERE county = %(county)s AND election_year = %(election_year)s AND (suggestion ~* %(tokens)s OR position ~* %(tokens)s OR brought_by ~* %(tokens)s)
    ''', data)
    return c.fetchone()[0]

def one_mayor_association_json(token):
    c.execute('''
        SELECT json_build_object('label', %(label)s, 'sum', COALESCE(SUM(approved_expense_avg), 0), 'count', COALESCE(COUNT(*), 0))
        FROM suggestions_suggestions
        WHERE county = %(county)s AND election_year = %(election_year)s AND (suggestion ~* %(label)s OR position ~* %(label)s OR brought_by ~* %(label)s)
    ''', data)
    return c.fetchone()[0]

c.execute('''
    SELECT uid, mayor_id, election_year, county
    FROM mayors_terms
''')
key = [desc[0] for desc in c.description]
for row in c.fetchall():
    data = dict(zip(key, row))
    c.execute('''
        UPDATE mayors_terms
        SET data = (COALESCE(data, '{}'::jsonb) || %s::jsonb)
        WHERE uid = %s
    ''', (json.dumps({'suggestions_years': one_mayor_term_years(data)}), data['uid']))

    piles = []
    for pile, tokens in [(u'協會', [u'協會', u'學會', u'商會', u'公會', u'協進會', u'促進會', u'研習會', u'婦聯會', u'婦女會', u'體育會', u'同心會', u'農會', u'早起會', u'健身會', u'宗親會', u'功德會', u'商業會', u'長青會', u'民眾服務社', u'聯盟']), (u'辦公室', [u'辦公室', u'辦公處']), (u'廟', [u'廟', u'宮']), (u'警察局', [u'警察局', u'分局']), (u'消防局', [u'消防局', u'消防隊', u'分隊', u'中隊']), (u'國中、國小', [u'國中', u'國小', u'中學', u'小學'])]:
        data.update({
            'label': pile,
            'tokens': u'%s' % u'|'.join(tokens)
        })
        r = one_mayor_pile_json(data)
        if r['sum']:
            piles.append(r)
    piles = sorted(piles, key=lambda x: x['sum'], reverse=True)
    c.execute('''
        UPDATE mayors_terms
        SET data = (COALESCE(data, '{}'::jsonb) || %s::jsonb)
        WHERE uid = %s
    ''', (json.dumps({'suggestions_piles': piles}), data['uid']))

    associations = []
    for token in [u'社區發展協會', u'學會', u'商會', u'公會', u'協進會', u'促進會', u'研習會', u'婦聯會', u'婦女會', u'體育會', u'同心會', u'農會', u'早起會', u'健身會', u'宗親會', u'功德會', u'商業會', u'長青會', u'民眾服務社', u'聯盟']:
        data.update({
            'label': token
        })
        r = one_mayor_association_json(token)
        if r['sum']:
            associations.append(r)
    associations = sorted(associations, key=lambda x: x['sum'], reverse=True)
    c.execute('''
        UPDATE mayors_terms
        SET data = (COALESCE(data, '{}'::jsonb) || %s::jsonb)
        WHERE uid = %s
    ''', (json.dumps({'suggestions_associations': associations}), data['uid']))
conn.commit()
