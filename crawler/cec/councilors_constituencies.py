# -*- coding: utf-8 -*-
import os
import re
import json
import urllib
from urlparse import urljoin
import scrapy


class Spider(scrapy.Spider):
    name = "councilors_constituencies"
    allowed_domains = ["db.cec.gov.tw"]
    start_urls = ["http://db.cec.gov.tw/",]
    download_delay = 1

    def __init__(self):
        with open(os.path.join(os.path.dirname(__file__), '../../data/cec/regional_constituencies_from_wikidata.json'), 'r') as infile:
            self.ref = json.loads(infile.read())

    def parse(self, response):
        for level in response.xpath(u'//a[re:test(., "^2014.+議員選舉$")]/@href').extract():
            yield response.follow(level, callback=self.parse_level)

    def parse_level(self, response):
        ref = {
            u'區域': {'constituency_type_title': u'區域', 'constituency_type': 'regional'},
            u'平原': {'constituency_type_title': u'平地原住民', 'constituency_type': 'ethnical'},
            u'山原': {'constituency_type_title': u'山地原住民', 'constituency_type': 'ethnical'},
            u'不分區政黨': {'constituency_type_title': u'全國不分區', 'constituency_type': 'PR'},
        }
        for region in response.xpath(u'//div[re:test(., "候選人得票明細")]/following-sibling::div/a'):
            yield response.follow(region.xpath('@href').extract_first(), callback=self.parse_region, meta={'meta': ref[region.xpath('text()').extract_first().strip()]})

    def parse_region(self, response):
        for constituency in response.css(u'table.ctks tr.data td[rowspan] a'):
            yield response.follow(constituency.xpath('@href').extract_first(), callback=self.parse_constituency, meta={'meta': response.meta['meta']})

    def parse_constituency(self, response):
        constituency_label = re.search(u'.+?選區', response.css(u'table.ctks tr.data td[rowspan] a').xpath('text()').extract_first()).group()
        print(constituency_label)
        county = re.sub(u'第\d+.+', '', constituency_label)
        constituency_number = int(re.sub('\D', '', constituency_label))
        print(county, constituency_number)
        d = {
            'constituency_type_title': response.meta['meta']['constituency_type_title'],
            'constituency_type': response.meta['meta']['constituency_type'],
            'constituency_label_wiki': u'%s議員第%d選舉區' % (county, constituency_number),
            'constituency_label': constituency_label,
            'county': county,
            'constituency_number': constituency_number,
            'districts': [],
        }
        for r in self.ref:
            if r['itemLabel'] == d['constituency_label_wiki']:
                d['wikidata_item'] = r['item']
                break
        for town in response.css(u'table.ctks tr.data td[rowspan] a'):
            print(town.xpath('text()').extract_first())
            town_label = re.sub(u'.+?選區', '', town.xpath('text()').extract_first())
            print(town_label)
            d['districts'].append(town_label)
        return d
