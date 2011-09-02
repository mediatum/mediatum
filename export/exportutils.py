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

import core.tree as tree
import core.athana as athana

from utils.utils import esc, u
from utils.date import parse_date, format_date

tagpattern = re.compile(r'<[^>]*?>')
def no_html(s):
    return tagpattern.sub('', s)
    
def prss(s):
    '''protect rss item elements'''
    return esc(no_html(esc(no_html(esc(no_html(esc(u(s))))))))    

def runTALSnippet(s, context, mask=None):
    header = '''<?xml version="1.0" encoding="UTF-8" ?>'''
    xmlns = '''<talnamespaces xmlns:tal="http://xml.zope.org/namespaces/tal" xmlns:metal="http://xml.zope.org/namespaces/metal">'''
    footer = '''</talnamespaces>'''
    cutter = "----cut-TAL-result-here----\n"
    
    if mask:
        header += mask.get('exportheader')
        footer += mask.get('exportfooter')

    to_be_processed = header + xmlns + cutter + s + cutter + footer
    wr_result = athana.getTALstr(to_be_processed, context, mode='xml')
    
    return wr_result[wr_result.find(cutter)+len(cutter):wr_result.rfind(cutter)]
 

def handleCommand(cmd, var, s, node, attrnode=None, field_value="", options=[], mask=None):

    if cmd=='cmd:getTAL':
        context = dict(node.items())
        # not all metafields may have values
        # default behavior should be taken care of in the TAL

        context['tree'] = tree
        context['node'] = node
        context['esc'] = esc  # may be needed for example in escaping rss item elements
        context['no_html'] = no_html 
        context['u'] = u 
        context['prss'] = prss # protect rss
        context['parse_date'] = parse_date 
        context['format_date'] = format_date
        
        result = runTALSnippet(s, context, mask)

        return result.replace("[" + var + "]", "")
