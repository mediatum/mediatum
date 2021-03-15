"""
 mediatum - a multimedia content repository

 Copyright (C) 2007 Arne Seifert <seiferta@in.tum.de>
 Copyright (C) 2007 Matthias Kramm <kramm@in.tum.de>
 Copyright (C) 2011 Werner F. Neudenberger <neudenberger@ub.tum.de>

 This program is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.

 This program is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
from __future__ import division

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
