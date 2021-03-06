# -*- coding: utf-8 -*-
import json
from django import forms
from django.utils.datastructures import MultiValueDict

from .models import Intent, Intent_Standpoints, User_Generate_List

types = (('councilors', u'縣市議員'), ('mayors', u'縣市長'), )
counties = ((x, x) for x in ["", "臺北市", "新北市", "桃園市", "基隆市", "宜蘭縣", "新竹縣", "新竹市", "苗栗縣", "臺中市", "彰化縣", "雲林縣", "南投縣", "嘉義縣", "嘉義市", "臺南市", "高雄市", "屏東縣", "花蓮縣", "臺東縣", "澎湖縣", "金門縣", "連江縣"])

parties = ((x, x) for x in ['', '無黨籍', '中國國民黨', '民主進步黨', '臺灣團結聯盟', '親民黨', '新黨', '人民民主陣線', '綠黨', '樹黨', '無黨團結聯盟', '臺灣第一民族黨', '臺灣建國黨', '臺灣民族黨', '華聲黨', '勞動黨', '中華民主向日葵憲政改革聯盟', '大道人民黨', '人民最大黨', '聯合黨', '臺灣主義黨', '中華統一促進黨', '健保免費連線', '民國黨', '大愛憲改聯盟', '時代力量', '自由臺灣黨', '基進黨', '軍公教聯盟黨', '綠黨社會民主黨聯盟', '社會民主黨', '信心希望聯盟', '臺灣國民會議', '中華民國臺灣基本法連線', '和平鴿聯盟黨', '臺灣獨立黨', '臺灣工黨', '社會福利黨', '泛盟黨', '正黨', '臺灣未來黨', '中華民國機車黨', '中國生產黨', '勞工黨', '中華台商愛國黨'])

class LinkWidget(forms.widgets.MultiWidget):
    def __init__(self, attrs={}):
        _widgets = (
            forms.widgets.TextInput(attrs={'placeholder': u'網站名稱'}),
            forms.widgets.TextInput(attrs={'placeholder': u'網址'}),
        )
        super(LinkWidget, self).__init__(_widgets, attrs)

    def decompress(self, value):
        return [value.get('note'), value.get('url')] if value else [None, None]

class LinksWidget(forms.widgets.MultiWidget):
    def __init__(self, attrs={}):
        _widgets = (
            LinkWidget(attrs=attrs),
            LinkWidget(attrs=attrs),
            LinkWidget(attrs=attrs),
        )
        super(LinksWidget, self).__init__(_widgets, attrs)

    def decompress(self, value):
        value = json.loads(value)
        return value if value else [None, None, None]

    def value_from_datadict(self, data, files, name):
        if isinstance(data, MultiValueDict):
            return [{
                'note': data.get(name + '_%d_0' % i, ''),
                'url': data.get(name + '_%d_1' % i, '')
            } for i in range(3)]
        return data.get(name, None)

class IntentForm(forms.ModelForm):
    class Meta:
        model = Intent
        fields = ['name', 'county', 'constituency', 'district', 'party', 'motivation', 'platform', 'ideology', 'experience', 'education', 'remark', 'links', 'video_link', 'slogan', 'status', 'type']
        widgets = {
            'type': forms.widgets.Select(choices=types, attrs={'class': 'form-control'}),
            'name': forms.widgets.TextInput(attrs={'class': 'form-control'}),
            'county': forms.widgets.Select(choices=counties, attrs={'class': 'form-control'}),
            'constituency': forms.widgets.Select(attrs={'class': 'form-control'}),
            'party': forms.widgets.Select(choices=parties, attrs={'class': 'form-control'}),
            'links': LinksWidget(attrs={'class': 'form-control'}),
            'slogan': forms.widgets.TextInput(attrs={
                'class': 'form-control',
                'placeholder': u'20字內'
            }),
            'video_link': forms.widgets.URLInput(attrs={
                'class': 'form-control',
                'placeholder': u'Youtube 影片連結'
            }),
        }

class SponsorForm(forms.Form):
    name = forms.CharField(label=u'姓名', max_length=100, required=False, help_text=u'選填')
    email = forms.EmailField(label=u'E-mail', max_length=254, required=False, help_text=u'選填')
    phone = forms.CharField(label=u'連絡電話', max_length=20, required=False, help_text=u'選填')
    votable = forms.NullBooleanField(label=u'可在此選區投票', required=False)

class Intent_StandpointsForm(forms.ModelForm):
    pro = forms.TypedChoiceField(
        choices=((True, u'贊成'), (False, u'反對')),
    )
    class Meta:
        model = Intent_Standpoints
        fields = ['pro', 'comment', ]
        widgets = {
            'pro': forms.widgets.Select(attrs={'class': 'form-control'}),
            'comment': forms.widgets.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class ListsForm(forms.ModelForm):
    class Meta:
        model = User_Generate_List
        fields = ['content', 'recommend', 'link']
        widgets = {
            'content': forms.widgets.Textarea(attrs={
                'class': 'form-control',
                'placeholder': u'範例:\n駱阿瓜\n駱瓜喵',
                'rows': 5
            }),
            'recommend': forms.widgets.Select(choices=((True, u'推薦'), (None, u'不表達'), (False, u'不推薦')), attrs={'class': 'form-control'}),
            'link': forms.widgets.URLInput(attrs={
                'class': 'form-control',
                'placeholder': u'外部網址，如臉書貼文網址，您對此份名單的詳細介紹，可發布後再編輯'
            }),
        }

