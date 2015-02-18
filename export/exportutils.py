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
import os
import inspect
import codecs
import logging

from mediatumtal import tal
import core.tree as tree
import core.config as config
import core.users as users

import utils.date as date

from utils.utils import esc, u, u2, esc2, utf82iso, iso2utf8
from utils.date import parse_date, format_date
from core.acl import AccessData

logg = logging.getLogger(__name__)

tagpattern = re.compile(r'<[^>]*?>')


def no_html(s):
    return tagpattern.sub('', s)


def prss(s):
    '''protect rss item elements'''
    return esc(no_html(esc(no_html(esc(no_html(esc(u(s))))))))


def cdata(s):
    return '<![CDATA[%s]]>' % s


def get_udate(node):
    try:
        return format_date(parse_date(node.get("updatetime")), "%Y-%m-%d")
    except:
        return format_date(date.now(), "%Y-%m-%d")


def getAccessRights(node):
    """ Get acccess rights for the public.
    The values returned descend from
    http://wiki.surffoundation.nl/display/standards/info-eu-repo/#info-eu-repo-AccessRights.
    This values are used by OpenAIRE portal.

    """
    try:  # if node.get('updatetime') is empty, the method parse_date would raise an exception
        l_date = parse_date(node.get('updatetime'))
    except:
        l_date = date.now()
    guestAccess = AccessData(user=users.getUser('Gast'))
    if date.now() < l_date:
        return "embargoedAccess"
    elif guestAccess.hasAccess(node, 'read'):
        if guestAccess.hasAccess(node, 'data'):
            return "openAccess"
        else:
            return "restrictedAccess"
    else:
        return "closedAccess"


def load_iso_639_2_b_names():
    filename = "ISO-639-2_utf-8.txt"
    try:
        abs_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
        abs_path = os.path.join(abs_dir, filename)
        with codecs.open(abs_path, 'rb', encoding='utf8') as f:
            text = f.read()
        lines = text.splitlines()
        logg.info("exportutils read file 'ISO-639-2_utf-8.txt': %d lines", len(lines))
    except:
        lines = []
        logg.warning("exportutils could not load file 'ISO-639-2_utf-8.txt'")
    return lines


iso_639_2_list = load_iso_639_2_b_names()


def normLanguage_iso_639_2_b(s, emptyval=''):
    """
    source: http://www.loc.gov/standards/iso639-2/ISO-639-2_utf-8.txt
    retrieved: 2013-05-02

    for oai_dc language tags
    using iso 639.2
    deciding for (b)ibliographic in case of b/t-ambiguity (t=terminology)

    http://en.wikipedia.org/wiki/Languages_used_on_the_Internet
    1 	English 	54.9%
    2 	Russian 	6.1%
    3 	German 	5.3%
    4 	Spanish 	4.8%
    5 	Chinese 	4.4%
    6 	French 	4.3%
    7 	Japanese 	4.2%
    8 	Portuguese 	2.3%
    9 	Polish 	1.8%
    10 	Italian 	1.5%

    (set of these languages corresponed on 2013-05-02 with most used languages
     on wikipedia encyclopedia)

    """
    s1 = s.strip().lower()

    if not s1:
        return emptyval

    s1 = s1[0:3]

    if s1 == 'en' or s1.startswith('en'):
        return 'eng'
    elif s1 == 'de' or s1.startswith('de') or s1.startswith('ger'):
        return 'ger'
    elif s1 == 'ru' or s1.startswith('rus'):
        return 'rus'
    elif s1 == 'fr' or s1.startswith('fre'):
        return 'fre'
    elif s1.startswith('ch'):
        return 'chi'
    elif s1 == 'jp' or s1.startswith('jap'):
        return 'jpn'
    elif s1 == 'es' or s1.startswith('spa'):
        return 'spa'
    elif s.lower().startswith('sonst'):
        return emptyval
    else:
        s2 = s1 + "|"
        s3 = "|" + s2
        for line in iso_639_2_list:
            if line.startswith(s2):
                return s1
            elif line.find(s3) > 0:
                return line.split("|")[0]
        logg.error('normLanguage_iso_639_2_b(...) -> language was not matched, returning emtyval="%s" s="%s", s1="%s"', emptyval, s, s1)
        return emptyval


def normLanguage_iso_639_2_t(s, emptyval=''):
    """
    source: http://www.loc.gov/standards/iso639-2/ISO-639-2_utf-8.txt
    retrieved: 2013-05-02

    for oai_dc language tags
    using iso 639.2
    deciding for (t)erminology in case of b/t-ambiguity

    http://en.wikipedia.org/wiki/Languages_used_on_the_Internet
    1 	English 	54.9%
    2 	Russian 	6.1%
    3 	German 	5.3%
    4 	Spanish 	4.8%
    5 	Chinese 	4.4%
    6 	French 	4.3%
    7 	Japanese 	4.2%
    8 	Portuguese 	2.3%
    9 	Polish 	1.8%
    10 	Italian 	1.5%

    (set of these languages corresponed on 2013-05-02 with most used languages
     on wikipedia encyclopedia)

    """
    s1 = s.strip().lower()

    if not s1:
        return emptyval

    s1 = s1[0:3]

    if s1 == 'en' or s1.startswith('en'):
        return 'eng'
    elif s1 == 'de' or s1.startswith('de') or s1.startswith('ger'):
        return 'deu'
    elif s1 == 'ru' or s1.startswith('rus'):
        return 'rus'
    elif s1 == 'fr' or s1.startswith('fre'):
        return 'fra'
    elif s1.startswith('ch'):
        return 'zho'
    elif s1 == 'jp' or s1.startswith('jap'):
        return 'jpn'
    elif s1 == 'es' or s1.startswith('spa'):
        return 'spa'
    elif s.lower().startswith('sonst'):
        return emptyval
    else:
        s2 = s1 + "|"
        s3 = "|" + s2
        for line in iso_639_2_list:
            _b, _t, _two, _english, _french = list.split('|')
            if s1 in [_b, _t]:
                if _t:
                    return _t
                else:
                    return _b
            elif line.find(s3) > 0:
                return line.split("|")[0]
        logg.error('normLanguage_iso_639_2_t(...) -> language was not matched, returning emtyval="%s" s="%s", s1="%s"', emptyval, s, s1)
        return emptyval


def runTALSnippet(s, context, mask=None):
    if s.find('tal:') < 0:
        return s

    header = '''<?xml version="1.0" encoding="UTF-8" ?>'''
    xmlns = '''<talnamespaces xmlns:tal="http://xml.zope.org/namespaces/tal" xmlns:metal="http://xml.zope.org/namespaces/metal">'''
    footer = '''</talnamespaces>'''
    cutter = "----cut-TAL-result-here----\n"

    if mask:
        exportheader = mask.get('exportheader')
        if exportheader.startswith("<?xml"):
            header = exportheader
        else:
            header += exportheader
        footer += mask.get('exportfooter')

    to_be_processed = header + xmlns + cutter + s + cutter + footer
    try:  # normally only encoding errors
        wr_result = tal.getTALstr(to_be_processed, context, mode='xml')
    except:  # try with u2 method
        try:
            wr_result = tal.getTALstr(u2(to_be_processed), context, mode='xml')
        except:
            wr_result = tal.getTALstr(u2(to_be_processed), context)
        #wr_result = tal.getTALstr(u2(to_be_processed), context, mode='xml')

    return wr_result[wr_result.find(cutter) + len(cutter):wr_result.rfind(cutter)]

default_context = {}
default_context['tree'] = tree
default_context['esc'] = esc  # may be needed for example in escaping rss item elements
default_context['esc2'] = esc2  # may be needed for example in escaping rss item elements
default_context['no_html'] = no_html
default_context['u'] = u
default_context['utf82iso'] = utf82iso
default_context['iso2utf8'] = iso2utf8
default_context['prss'] = prss  # protect rss
default_context['parse_date'] = parse_date
default_context['format_date'] = format_date
default_context['cdata'] = cdata
default_context['get_udate'] = get_udate
default_context['getAccessRights'] = getAccessRights
default_context['config_get'] = config.get
default_context['normLanguage_iso_639_2_b'] = normLanguage_iso_639_2_b
default_context['normLanguage_iso_639_2_t'] = normLanguage_iso_639_2_t


def registerDefaultContextEntry(key, entry):
    default_context[key] = entry


def handleCommand(cmd, var, s, node, attrnode=None, field_value="", options=[], mask=None):
    from web.frontend.streams import build_filelist, get_transfer_url
    if cmd == 'cmd:getTAL':
        context = default_context.copy()
        context['node'] = node
        context['build_filelist'] = build_filelist
        context['get_transfer_url'] = get_transfer_url
        result = runTALSnippet(s, context, mask)

        return result.replace("[" + var + "]", "")
