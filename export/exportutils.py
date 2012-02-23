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

import re
import string
import logging

import core.tree as tree
import core.athana as athana
import core.config as config

import utils.date as date

from utils.utils import esc, u, u2
from utils.date import parse_date, format_date

import oaisets

tagpattern = re.compile(r'<[^>]*?>')
def no_html(s):
    return tagpattern.sub('', s)
    
def prss(s):
    '''protect rss item elements'''
    return esc(no_html(esc(no_html(esc(no_html(esc(u(s))))))))    
    
def cdata(s):
    return '<![CDATA[%s]]>' % s  
    
def get_udate(node):
    udate = node.get("updatetime")
    if udate:
        udate = parse_date(udate)
    else:
        udate = date.now()
    return format_date(udate, "%Y-%m-%d") 
    
def runTALSnippet(s, context, mask=None):
    if s.find('tal:') < 0:
        return s
        
    header = '''<?xml version="1.0" encoding="UTF-8" ?>'''
    xmlns = '''<talnamespaces xmlns:tal="http://xml.zope.org/namespaces/tal" xmlns:metal="http://xml.zope.org/namespaces/metal">'''
    footer = '''</talnamespaces>'''
    cutter = "----cut-TAL-result-here----\n"
    
    if mask:
        header += mask.get('exportheader')
        footer += mask.get('exportfooter')

    to_be_processed = header + xmlns + cutter + s + cutter + footer
    try: # normally only encoding errors
        wr_result = athana.getTALstr(to_be_processed, context, mode='xml')
    except: # try with u2 method
        wr_result = athana.getTALstr(u2(to_be_processed), context, mode='xml')
    
    return wr_result[wr_result.find(cutter)+len(cutter):wr_result.rfind(cutter)]
 
default_context = {} 
default_context['tree'] = tree
default_context['esc'] = esc  # may be needed for example in escaping rss item elements
default_context['no_html'] = no_html 
default_context['u'] = u 
default_context['prss'] = prss # protect rss
default_context['parse_date'] = parse_date 
default_context['format_date'] = format_date
default_context['cdata'] = cdata
default_context['get_udate'] = get_udate        
default_context['config_get'] = config.get

def registerDefaultContextEntry(key, entry):
    global default_context
    default_context[key] = entry

def handleCommand(cmd, var, s, node, attrnode=None, field_value="", options=[], mask=None):
    from web.frontend.streams import build_filelist, get_transfer_url
    global default_context
    
    if cmd=='cmd:getTAL':
        context = default_context.copy()
        context['node'] = node
        context['build_filelist'] = build_filelist
        context['get_transfer_url'] = get_transfer_url        
        result = runTALSnippet(s, context, mask)

        return result.replace("[" + var + "]", "")
