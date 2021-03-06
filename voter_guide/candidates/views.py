# -*- coding: utf-8 -*-
import re
import json
import uuid
import itertools
import requests
from random import randint

from django.shortcuts import render, get_object_or_404, redirect
from django.db import connections, transaction
from django.db.models import Case, When, Value, Count, Sum, Q, F
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from .models import Candidates, Terms, Intent, Intent_Likes, User_Generate_List
from .forms import IntentForm, SponsorForm, ListsForm
from councilors.models import CouncilorsDetail
from suggestions.models import Suggestions
from platforms.models import Platforms
from elections.models import Elections
from commontag.views import paginate, coming_election_year
from .tasks import intent_register_achievement, intent_like_achievement


def populate_standpoints(candidates):
    c = connections['default'].cursor()
    standpoints = {}
    for candidate in candidates:
        if candidate.type == 'mayors':
            terms = Terms.objects.filter(type='mayors', candidate_id=candidate.candidate_id, elected=True)\
                                .order_by('-election_year')
            terms_id = tuple([x.uid for x in terms])
            for term in terms:
                qs = u'''
                    SELECT json_agg(row)
                    FROM (
                        SELECT
                            s.title,
                            count(*) as times,
                            sum(pro) as pro,
                            json_agg((select x from (select v.uid, v.abstract) x)) as bills
                        FROM bills_mayors_bills lv
                        JOIN standpoints_standpoints s on s.bill_id = lv.bill_id
                        JOIN bills_bills v on lv.bill_id = v.uid
                        WHERE lv.mayor_id in %s AND s.pro = (
                            SELECT max(pro)
                            FROM standpoints_standpoints ss
                            WHERE ss.pro > 0 AND s.bill_id = ss.bill_id
                            GROUP BY ss.bill_id
                        )
                        GROUP BY s.title
                        ORDER BY pro DESC, times DESC
                        LIMIT 3
                    ) row
                '''
                c.execute(qs, [terms_id, ])
                r = c.fetchone()
                standpoints.update({candidate.id: {'county': term.county, 'election_year': term.election_year, 'standpoints': r[0] if r else []}})
        else:
            if candidate.councilor_terms:
                terms_id = tuple([x['term_id'] for x in candidate.councilor_terms])
                c = connections['default'].cursor()
                qs = u'''
                    SELECT jsonb_object_agg(k, v)
                    FROM (
                        SELECT 'votes' as k, json_agg(row) as v
                        FROM (
                            SELECT
                                CASE
                                    WHEN lv.decision = 1 THEN '贊成'
                                    WHEN lv.decision = -1 THEN '反對'
                                    WHEN lv.decision = 0 THEN '棄權'
                                    WHEN lv.decision isnull THEN '沒投票'
                                END as decision,
                                s.title,
                                count(*) as times,
                                sum(pro) as pro,
                                json_agg((select x from (select v.uid, v.content) x)) as votes
                            FROM votes_councilors_votes lv
                            JOIN standpoints_standpoints s on s.vote_id = lv.vote_id
                            JOIN votes_votes v on lv.vote_id = v.uid
                            WHERE lv.councilor_id in %s AND s.pro = (
                                SELECT max(pro)
                                FROM standpoints_standpoints ss
                                WHERE ss.pro > 0 AND s.vote_id = ss.vote_id
                                GROUP BY ss.vote_id
                            )
                            GROUP BY s.title, lv.decision
                            ORDER BY pro DESC, times DESC
                            LIMIT 3
                        ) row
                        UNION ALL
                        SELECT 'bills' as k, json_agg(row) as v
                        FROM (
                            SELECT
                                CASE
                                    WHEN priproposer = true AND petition = false THEN '主提案'
                                    WHEN petition = false THEN '共同提案'
                                    WHEN petition = true THEN '連署提案'
                                END as role,
                                s.title,
                                count(*) as times,
                                sum(pro) as pro,
                                json_agg((select x from (select v.uid, v.abstract) x)) as bills
                            FROM bills_councilors_bills lv
                            JOIN standpoints_standpoints s on s.bill_id = lv.bill_id
                            JOIN bills_bills v on lv.bill_id = v.uid
                            WHERE lv.councilor_id in %s AND s.pro = (
                                SELECT max(pro)
                                FROM standpoints_standpoints ss
                                WHERE ss.pro > 0 AND s.bill_id = ss.bill_id
                                GROUP BY ss.bill_id
                            )
                            GROUP BY s.title, role
                            ORDER BY pro DESC, times DESC
                            LIMIT 3
                        ) row
                    ) r
                '''
                c.execute(qs, [terms_id, terms_id])
                r = c.fetchone()
                standpoints.update({candidate.id: r[0] if r else []})
    return standpoints

def populate_candidates(request, coming_ele_year, chosen_candidates):
    county = request.COOKIES.get('county')
    candidates = Terms.objects.filter(election_year=coming_ele_year, candidate_id__in=chosen_candidates).select_related('candidate', 'intent').order_by(
                                Case(
                                    When(county=county, then=Value(0)),
                                ), 'county', 'constituency')
    standpoints = populate_standpoints(candidates)
    groups = itertools.groupby(candidates, key=lambda x: (x.county, x.constituency))
    index = 0
    group_candidates = []
    for k, v in groups:
        v = list(v)
        group_candidates.append({'type': k, 'items': v, 'base_count': index})
        index += len(v)
    standpoints = populate_standpoints(candidates)
    return group_candidates, index, standpoints

def intents(request, election_year):
    ref = {
        'create_at': 'id',
        'likes': 'likes'
    }
    order_by = ref.get(request.GET.get('order_by'), 'likes')
    qs = Q(county=request.GET.get('county')) if request.GET.get('county') else Q()
    qs = qs & Q(election_year=election_year) & ~Q(status='draft')
    qs = qs & Q(constituency__in=request.GET.get('constituency').split(',')) if request.GET.get('constituency') else qs
    intents = Intent.objects.filter(qs).order_by('-%s' % order_by)
    intents = paginate(request, intents)
    intent_counties = Intent.objects.filter(qs).values('county').annotate(count=Count('county'))
    return render(request, 'candidates/intents.html', {'intents': intents, 'intent_counties': intent_counties, 'election_year': election_year})

def mayors_area(request, election_year):
    return render(request, 'candidates/mayors_area.html', {'election_year': election_year})

def mayors(request, election_year, county):
    coming_ele_year = coming_election_year(county)
    if election_year == coming_ele_year:
        if request.GET.get('name'):
            candidates = Terms.objects.filter(election_year=election_year, county=county, type='mayors', status='register').select_related('candidate', 'intent').order_by(
                                  Case(
                                      When(name=request.GET['name'], then=Value(0)),
                              ), '?')
        else:
            candidates = Terms.objects.filter(election_year=election_year, county=county, type='mayors', status='register').select_related('candidate', 'intent').order_by('?')
    else:
        candidates = Terms.objects.filter(election_year=election_year, county=county, type='mayors', status='register').select_related('candidate', 'intent').order_by('-votes')
    years = Terms.objects.filter(county=county, type='mayors').values_list('election_year', flat=True).distinct().order_by('-election_year')
    standpoints = populate_standpoints(candidates)
    return render(request, 'candidates/mayors.html', {'years': years, 'election_year': election_year, 'county': county, 'candidates': candidates, 'standpoints': standpoints})

def councilors_area(request, election_year):
    return render(request, 'candidates/councilors_area.html', {'election_year': election_year})

def councilors_districts(request, election_year, county):
    return render(request, 'candidates/councilors_districts.html', {'election_year': election_year, 'county': county})

def district(request, election_year, county, constituency):
    coming_ele_year = coming_election_year(county)
    constituencies = {}
    try:
        election_config = Elections.objects.get(id=election_year).data
        constituencies = election_config.get('constituencies', {})
    except:
        constituencies = {}
    years = Terms.objects.filter(county=county, type='councilors', constituency=constituency).values_list('election_year', flat=True).distinct().order_by('-election_year')
    if election_year == coming_ele_year:
        if request.GET.get('name'):
            candidates = Terms.objects.filter(election_year=election_year, county=county, type='councilors', constituency=constituency, status='register').select_related('candidate', 'intent').order_by(
                Case(
                    When(name=request.GET['name'], then=Value(0)),
            ), '?')
        else:
            candidates = Terms.objects.filter(election_year=election_year, county=county, type='councilors', constituency=constituency, status='register').select_related('candidate', 'intent').order_by('?')
    else:
        candidates = Terms.objects.filter(election_year=election_year, county=county, type='councilors', constituency=constituency).select_related('candidate', 'intent').order_by('-votes')
    standpoints = populate_standpoints(candidates)
    return render(request, 'candidates/district.html', {'years': years, 'coming_election_year': coming_ele_year, 'election_year': election_year, 'county': county, 'constituency': constituency, 'constituencies': constituencies, 'district': constituencies[county]['regions'][int(constituency)-1]['district'] if constituencies.get(county) else '', 'cec_data': constituencies[county]['regions'][int(constituency)-1] if constituencies.get(county) else {}, 'candidates': candidates, 'standpoints': standpoints, 'random_row': randint(1, len(candidates)) if not request.GET.get('intent') and len(candidates) else 1})

def intent_home(request):
    return render(request, 'candidates/intent_home.html', )

def intent_upsert(request):
    election_year = coming_election_year(None)
    if not request.user.is_authenticated:
        return redirect(reverse('candidates:intent_home'))
    try:
        instance = Intent.objects.get(user=request.user, election_year=election_year)
    except:
        instance = None
    if request.method == 'GET':
        form = IntentForm(instance=instance)
        form.fields['name'].initial = request.user.last_name + request.user.first_name
        form.fields['links'].initial = [{'note': u'Facebook 個人頁面', 'url': request.user.socialaccount_set.first().get_profile_url()}, None, None]
    if request.method == 'POST':
        form = IntentForm(request.POST, instance=instance)
        if form.has_changed() and form.is_valid():
            intent = form.save(commit=False)
            if intent.user_id and request.user.id != intent.user_id:
                return redirect(reverse('candidates:intent_home'))
            intent.user = request.user
            if instance and instance.status == 'intent_apply':
                intent.status = 'intent_apply'
            if intent.type == 'mayors':
                intent.constituency = 0
                intent.district = ''
            intent.save()
            c = connections['default'].cursor()
            history = request.POST.copy()
            history.pop('csrfmiddlewaretoken', None)
            history['links'] = intent.links
            history['modify_at'] = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
            c.execute('''
                UPDATE candidates_intent
                SET history = (%s::jsonb || COALESCE(history, '[]'::jsonb))
                WHERE user_id = %s AND election_year = %s
            ''', [json.dumps([history]), request.user.id, election_year])
            intent_register_achievement(request.user)
        return redirect(reverse('candidates:intent_detail', kwargs={'intent_id': instance.uid if instance else intent.uid}))
    return render(request, 'candidates/intent_upsert.html', {'form': form, 'election_year': election_year})

def intent_detail(request, intent_id):
    intent = get_object_or_404(Intent.objects.select_related('user'), uid=intent_id)
    if intent.status == 'draft' and request.user.id != intent.user_id:
        return redirect(reverse('candidates:intent_home'))
    c = connections['default'].cursor()
    c.execute(u'''
        SELECT json_agg(r)
        FROM (
            SELECT *
            FROM (
                SELECT *
                FROM (
                    SELECT
                        cis.pro as decision,
                        s.title,
                        count(*) as times,
                        sum(s.pro) as pro,
                        json_agg((select x from (select b.uid, b.abstract, b.proposed_by, b.param, cis.comment) x)) as detail
                    FROM candidates_intent_standpoints cis
                    JOIN standpoints_standpoints s on s.bill_id = cis.bill_id
                    JOIN bills_bills b on cis.bill_id = b.uid
                    WHERE cis.intent_id = %s AND s.county = %s AND s.pro = (
                        SELECT max(pro)
                        FROM standpoints_standpoints ss
                        WHERE ss.pro > 0 AND s.bill_id = ss.bill_id
                        GROUP BY ss.bill_id
                    )
                    GROUP BY cis.pro, s.title
                ) row
                UNION ALL
                SELECT *
                FROM (
                    SELECT
                        cis.pro as decision,
                        s.title,
                        count(*) as times,
                        sum(s.pro) as pro,
                        json_agg((select x from (select v.uid, v.content, cis.comment) x)) as detail
                    FROM candidates_intent_standpoints cis
                    JOIN standpoints_standpoints s on s.vote_id = cis.vote_id
                    JOIN votes_votes v on cis.vote_id = v.uid
                    WHERE cis.intent_id = %s AND s.county = %s AND s.pro = (
                        SELECT max(pro)
                        FROM standpoints_standpoints ss
                        WHERE ss.pro > 0 AND s.vote_id = ss.vote_id
                        GROUP BY ss.vote_id
                    )
                    GROUP BY cis.pro, s.title
                ) row
                ORDER BY decision, pro DESC
            ) rr
        ) r
    ''', [intent_id, intent.county, intent_id, intent.county])
    r = c.fetchone()
    standpoints = r[0] if r else []
    user_liked, form = False, None
    if request.user.is_authenticated:
        user_liked = Intent_Likes.objects.filter(intent_id=intent_id, user=request.user)
        if request.method == 'POST':
            if request.POST.get('decision') == 'upvote' and not user_liked:
                form = SponsorForm(request.POST)
                post = request.POST.dict()
                post.pop('csrfmiddlewaretoken', None)
                post['votable'] = {'1': u'未知', '2': u'是', '3': u'否', }.get(post['votable'])
                with transaction.atomic():
                    Intent_Likes.objects.create(intent_id=intent_id, user=request.user, data={'contact_details': post})
                    intent.likes += 1
                    intent.save(update_fields=['likes'])
                    user_liked = True
                intent_like_achievement(request.user, intent.likes > 99)
            elif request.POST.get('decision') == 'downvote' and user_liked:
                with transaction.atomic():
                    Intent_Likes.objects.filter(intent_id=intent_id, user=request.user).delete()
                    intent.likes -= 1
                    intent.save(update_fields=["likes"])
                    user_liked = False
        if not user_liked:
            form = SponsorForm()
            form.fields['name'].initial = request.user.last_name + request.user.first_name
            form.fields['email'].initial = request.user.email
    return render(request, 'candidates/intent_detail.html', {'form': form, 'intent': intent, 'standpoints': standpoints, 'user_liked': user_liked, 'is_this_intent': intent.user == request.user, 'id': 'profile'})

def intent_sponsor(request, intent_id):
    if not request.user.is_authenticated:
        return redirect(reverse('candidates:intent_detail', kwargs={'intent_id': intent_id}))
    intent = get_object_or_404(Intent.objects.select_related('user'), uid=intent_id, user=request.user)
    sponsors = Intent_Likes.objects.filter(intent_id=intent_id).order_by('-create_at')
    sponsors = paginate(request, sponsors)
    return render(request, 'candidates/intent_sponsor.html', {'sponsors': sponsors})

def pc(request, candidate_id, election_year):
    candidate = get_object_or_404(Terms.objects, election_year=election_year, candidate_id=candidate_id)
    return render(request, 'candidates/pc.html', {'candidate': candidate})

def get_candidates(name):
    c = connections['default'].cursor()
    identifiers = {name, re.sub(u'[\w。˙・･•．.‧’〃\']', '', name), re.sub(u'\W', '', name).lower(), } - {''}
    if identifiers:
        c.execute('''
            SELECT jsonb_agg(uid)
            FROM candidates_candidates
            WHERE identifiers ?| array[%s]
        ''' % ','.join(["'%s'" % x for x in identifiers]))
        r = c.fetchone()
        if r:
            return r[0]
    return []

def get_intents(name):
    c = connections['default'].cursor()
    identifiers = {name, re.sub(u'[\w。˙・･•．.‧’〃\']', '', name), re.sub(u'\W', '', name).lower(), } - {''}
    if identifiers:
        c.execute('''
            SELECT jsonb_agg(uid)
            FROM candidates_intent
            WHERE name in %s
        ''', [tuple(identifiers)])
        r = c.fetchone()
        if r:
            return r[0]
    return []

@login_required
def user_generate_list(request):
    try:
        instance = User_Generate_List.objects.get(user=request.user, uid=request.GET['list_id'])
    except:
        instance = None
    try:
        r = requests.get('https://graph.facebook.com/me/accounts', params={'type': 'page', 'access_token': request.user.socialaccount_set.first().socialtoken_set.first().token})
        fb_pages = [{'id': x['id'], 'name': x['name']} for x in r.json().get('data', []) if 'ADMINISTER' in x['perms']]
    except:
        fb_pages = []
    if request.method == 'POST':
        if request.POST.get('fb_page') and fb_pages:
            for x in fb_pages:
                if x['id'] == request.POST['fb_page']:
                    fb_page = {'id': x['id'], 'name': x['name']}
                    break
        else:
            fb_page = None
        chosen_candidates, chosen_intents = [], []
        form = ListsForm(request.POST, instance=instance)
        if form.is_valid():
            text = request.POST['content']
            text = text.strip(u'[　\s]')
            text = re.sub(u'[　\n、,]', u' ', text)
            text = re.sub(u'[ ]+(\d+)[ ]+', u'\g<1>', text)
            text = re.sub(u' ([^ \w]) ([^ \w]) ', u' \g<1>\g<2> ', text) # e.g. 楊　曜=>楊曜, 包含句首
            text = re.sub(u'^([^ \w]) ([^ \w]) ', u'\g<1>\g<2> ', text) # e.g. 楊　曜=>楊曜, 包含句首
            text = re.sub(u' ([^ \w]) ([^ \w])$', u' \g<1>\g<2>', text) # e.g. 楊　曜=>楊曜, 包含句尾
            text = re.sub(u' (\w+) (\w+) ', u' \g<1>\g<2> ', text) # e.g. Kolas Yotaka=>KolasYotaka, 包含句首
            text = re.sub(u'^(\w+) (\w+) ', u'\g<1>\g<2> ', text) # e.g. Kolas Yotaka=>KolasYotaka, 包含句首
            text = re.sub(u'　(\w+) (\w+)$', u' \g<1>\g<2>', text) # e.g. Kolas Yotaka=>KolasYotaka, 包含句尾
            text = re.sub(u'^([^ \w]) ([^ \w])$', u'\g<1>\g<2>', text) # e.g. 楊　曜=>楊曜, 單獨一人
            text = re.sub(u'^(\w+) (\w+)$', u'\g<1>\g<2>', text) # e.g. Kolas Yotaka=>KolasYotaka, 單獨一人
            for name in text.split():
                name = re.sub(u'(.*)[）)。】」]$', '\g<1>', name) # 名字後有標點符號
                uid = get_candidates(name)
                if uid:
                    chosen_candidates.extend(uid)
            if not request.POST.get('publish'):
                coming_ele_year = coming_election_year(None)
                recommend = None
                if form.instance:
                    if form.instance.recommend == True:
                        recommend = u'推薦'
                    elif form.instance.recommend == False:
                        recommend = u'不推薦'
                group_candidates, total_count, standpoints = populate_candidates(request, coming_ele_year, chosen_candidates)
                return render(request, 'candidates/user_generate_list.html', {'form': form, 'election_year': coming_ele_year, 'group_candidates': group_candidates, 'standpoints': standpoints, 'user': request.user, 'total_count': total_count, 'recommend': recommend, 'link': form.instance.link, 'id': 'profile', 'fb_pages': fb_pages, 'fb_page': fb_page})
            else:
                user_list = form.save(commit=False)
                if user_list.user_id and request.user.id != user_list.user_id:
                    return redirect(reverse('candidates:user_generate_list'))
                user_list.user = request.user
                user_list.publish = True
                user_list.data = {'candidates': chosen_candidates, 'fb_page': fb_page}
                user_list.save()
                return redirect(reverse('candidates:user_generated_list', kwargs={'list_id': user_list.uid}))
        form = ListsForm(instance=instance)
    elif instance:
        form = ListsForm(instance=instance)
        recommend = None
        if instance.recommend == True:
            recommend = u'推薦'
        elif instance.recommend == False:
            recommend = u'不推薦'
        coming_ele_year = coming_election_year(None)
        chosen_candidates = instance.data['candidates']
        group_candidates, total_count, standpoints = populate_candidates(request, coming_ele_year, chosen_candidates)
        return render(request, 'candidates/user_generate_list.html', {'form': form, 'election_year': coming_ele_year, 'group_candidates': group_candidates, 'standpoints': standpoints, 'user': instance.user, 'total_count': total_count, 'recommend': recommend, 'link': instance.link, 'id': 'profile', 'fb_pages': fb_pages, 'fb_page': instance.data.get('fb_page')})
    else:
        form = ListsForm(instance=instance)
        lists = User_Generate_List.objects.filter(user=request.user)
    return render(request, 'candidates/user_generate_list.html', {'form': form, 'lists': lists, 'fb_pages': fb_pages, 'id': 'profile'})

def user_generated_list(request, list_id):
    coming_ele_year = coming_election_year(None)
    try:
        user_list = User_Generate_List.objects.get(uid=list_id, publish=True)
        recommend = None
        if user_list.recommend == True:
            recommend = u'推薦'
        elif user_list.recommend == False:
            recommend = u'不推薦'
        chosen_candidates = user_list.data['candidates']
        group_candidates, total_count, standpoints = populate_candidates(request, coming_ele_year, chosen_candidates)
    except Exception, e:
        return HttpResponseRedirect('/')
    return render(request, 'candidates/user_generate_list.html', {'election_year': coming_ele_year, 'user_list': user_list, 'group_candidates': group_candidates, 'standpoints': standpoints, 'user': user_list.user, 'total_count': total_count, 'recommend': recommend, 'id': 'profile'})
