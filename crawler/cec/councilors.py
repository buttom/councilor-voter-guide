# -*- coding: utf-8 -*-
import os
import re
import json
import scrapy


class Spider(scrapy.Spider):
    name = "councilors"
    allowed_domains = ["db.cec.gov.tw"]
    start_urls = ["http://db.cec.gov.tw/",]
    download_delay = 1

    def __init__(self, election_year=None, *args, **kwargs):
        super(Spider, self).__init__(*args, **kwargs)
        self.election_year = election_year

    def parse(self, response):
        for level in response.xpath(u'//a[re:test(., "^%s.+議員選舉$")]/@href' % self.election_year).extract():
            yield response.follow(level, callback=self.parse_level)

    def parse_level(self, response):
        for category in response.xpath(u'//div[re:test(., "候選人得票明細")]/following-sibling::div/a/@href').extract():
            yield response.follow(category, callback=self.parse_list)

    def parse_list(self, response):
        category = response.css('.head::text').re(u'（(.+?)）')[0]
        for tr in response.css(u'table.ctks tr.data'):
            d = {
                'category': category,
                'county': tr.xpath('td[@rowspan]/a/text()').extract_first()
            }
            if d['county']:
                county = d['county']
                d['name'] = tr.xpath('td[2]/a/text()').extract_first().strip()
                for i, key in enumerate(['number', 'gender', 'birth_year', 'party', 'votes', 'votes_percentage', 'elected', 'occupy'], start=3):
                    d[key] = tr.xpath('td[%d]/text()' % i).extract_first().strip()
                yield response.follow(tr.xpath('td[2]/a/@href').extract_first(), callback=self.parse_person, meta={'meta': d})
            else:
                d['county'] = county
                d['name'] = tr.xpath('td[1]/a/text()').extract_first().strip()
                for i, key in enumerate(['number', 'gender', 'birth_year', 'party', 'votes', 'votes_percentage', 'elected', 'occupy'], start=2):
                    v = tr.xpath('td[%d]/text()' % i).extract_first()
                    d[key] = v.strip() if v else None
                yield response.follow(tr.xpath('td[1]/a/@href').extract_first(), callback=self.parse_person, meta={'meta': d})

    def parse_person(self, response):
        d = response.meta['meta']
        d['votes_detail'] = []
        for tr in response.css(u'table.ctks tr.data'):
            d['votes_detail'].append({
                'district': re.sub(u'^%s' % d['county'], '', tr.xpath('td[1]/a/text()').extract_first()),
                'votes': tr.xpath('td[4]/text()').extract_first(),
                'votes_percentage': tr.xpath('td[5]/text()').extract_first().strip()
            })
        yield d
