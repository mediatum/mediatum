# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import re

from utils.date import parse_date, format_date

date_pattern_standard = re.compile(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', re.UNICODE)
date_pattern_armus = re.compile(r'\d{2}/\d{2}/\d{4}', re.UNICODE)

# list of node attributes checked for rss item date
attr_list = ['updatetime', 'creationtime', 'evaluna-last-update', 'armus-datecreate', 'updatesearchindex']


def try_node_date(node, attr_list=attr_list):
    for key in attr_list:
        timevalue = node.get(key)
        if date_pattern_standard.match(timevalue):
            rfc822_time = format_date(parse_date(timevalue), 'rfc822')
            break
        elif date_pattern_armus.match(timevalue):
            rfc822_time = format_date(parse_date(timevalue, format="%m/%d/%Y"), 'rfc822')
            break
        else:
            rfc822_time = u''
    return rfc822_time

feed_channel_dict = {
    'title': '',
    'link': '',
    'description': '',
    'lang': '',
    'pubdate': '',
    'lastbuild': '',
}

template_rss_channel = u'''<?xml version="1.0" encoding="utf-8" standalone="yes"?>
<rss xmlns:content="http://purl.org/rss/1.0/modules/content/" version="2.0">
<channel>
<title>%(title)s</title>
<link>%(link)s</link>
<description>%(description)s</description>
<language>%(lang)s</language>
<pubDate>%(pubdate)s</pubDate>
<lastBuildDate>%(lastbuild)s</lastBuildDate>
%(items)s
</channel>
</rss>
'''

template_rss_item = u'''
<item>
<title>%(title)s</title>
<link>%(link)s</link>
<description><![CDATA[%(description)s]]></description>
%(categories)s
<pubDate>%(item_pubDate)s</pubDate>
<guid>%(guid)s</guid>
</item>
'''
