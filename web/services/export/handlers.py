"""
 mediatum - a multimedia content repository

 Copyright (C) 2007 Arne Seifert <seiferta@in.tum.de>
 Copyright (C) 2007 Matthias Kramm <kramm@in.tum.de>
 Copyright (C) 2011 Werner Neudenberger <neudenberger@ub.tum.de>

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

import json
import os
import re
import time
import logging

import core.tree as tree
import core.users as users
import core.xmlnode as xmlnode
import copy

from core import config
from core.acl import AccessData
from schema.schema import getMetaType, VIEW_DATA_ONLY

from utils.date import format_date
from utils.pathutils import getBrowsingPathList, isDescendantOf
from utils.utils import u, u2, esc, intersection, getMimeType, modify_tex

import web.services.jsonnode as jsonnode
from web.services.rssnode import template_rss_channel, template_rss_item, feed_channel_dict, try_node_date
from web.services.serviceutils import attribute_name_filter


logger = logging.getLogger('services')
host = "http://" + config.get("host.name")

guestAccess = AccessData(user=users.getUser('Gast'))
collections = tree.getRoot('collections')
home = tree.getRoot('home')

from web.services.cache import Cache
from web.services.cache import date2string as cache_date2string
import web.services.serviceutils as serviceutils

FILTERCACHE_NODECOUNT_THRESHOLD = 2000000

filtercache = Cache(maxcount=10, verbose=True)
searchcache = Cache(maxcount=10, verbose=True)
resultcache = Cache(maxcount=25, verbose=True)

SEND_TIMETABLE = False


def escape_illegal_xml_chars(val, replacement=''):
    illegal_xml_chars_re = re.compile(u'[\x00-\x08\x0b\x0c\x0e-\x1F\uD800-\uDFFF\uFFFE\uFFFF]')
    return illegal_xml_chars_re.sub(replacement, val)


def struct2xml(req, path, params, data, d, debug=False, singlenode=False, send_children=False, send_timetable=SEND_TIMETABLE):

    def attr_list_join(attr_list):
        sformat = '''<attribute name="%s"><![CDATA[%s]]></attribute>'''
        r = ''
        for attr in attr_list:
            if attribute_name_filter(attr[0]):
                r += (sformat % (attr[0], u(attr[1])))
        return r

    atime = starttime = time.time()

    # file types not to be included in listed node files
    exclude_filetypes = ['statistic']

    # sortfields
    sfields = d.setdefault('sfields', [])

    # mask
    mask = req.params.get('mask', 'default').lower()
    maskcachetype = req.params.get('maskcache', 'deep')  # 'deep', 'shallow', 'none'

    user_info = 'oauthuser="%s" username="%s" userid="%s"' % (d.get('oauthuser', ''), d.get('username', ''), d.get('userid', ''))

    res = '<?xml version="1.0" encoding="utf-8"?>\r\n'
    res += '<response status="%s" retrievaldate="%s" servicereactivity="%s sec." %s>\r\n' % (
        d['status'], d['retrievaldate'], d['dataready'], user_info)
    if d['status'] == 'ok':
        if singlenode:
            n = d['nodelist'][0]
            if not send_children:
                res += xmlnode.getSingleNodeXML(n, exclude_filetypes=exclude_filetypes, attribute_name_filter=attribute_name_filter)
            else:
                res += xmlnode.getNodeListXMLForUser(n, readuser='Gast',
                                                     exclude_filetypes=exclude_filetypes, attribute_name_filter=attribute_name_filter)

            # mask handling
            formated = n.show_node_text(labels=1, language=req.params.get('lang', ''), cachetype=maskcachetype)
            if mask not in ["", "none"]:  # deliver every mask
                try:
                    mask_obj = getMetaType(n.getSchema()).getMask(mask)
                except:
                    mask_obj = None
                if mask_obj:
                    formated = mask_obj.getViewHTML([n], flags=8)
                else:
                    mask = 'default'
            res = '%s\n    <mask name="%s"><![CDATA[%s]]></mask>\n%s' % (res[:-9], mask, formated, res[-8:])

        else:
            res += '<nodelist start="%d" count="%d" countall="%d">\r\n' % (d['nodelist_start'], d['nodelist_limit'], d['nodelist_countall'])
            for n in d['nodelist']:
                res += xmlnode.getSingleNodeXML(n, exclude_filetypes=exclude_filetypes, attribute_name_filter=attribute_name_filter)

                # mask handling
                formated = n.show_node_text(labels=1, language=req.params.get('lang', ''), cachetype=maskcachetype)
                if mask not in ["", "none"]:  # deliver every mask
                    try:
                        mask_obj = getMetaType(n.getSchema()).getMask(mask)
                    except:
                        mask_obj = None
                    if mask_obj:
                        formated = mask_obj.getViewHTML([n], flags=8)
                    else:
                        mask = 'default'
                res = '%s\n    <mask name="%s"><![CDATA[%s]]></mask>\n%s' % (res[:-9], mask, formated, res[-8:])

            res += '</nodelist>\r\n'

        # append a shortlist with id, name and type of the nodes
        # from result_shortlist = [[i, x.id, x.name, x.type, attr_list(x, sfields)] for i, x in enumerate(nodelist)]
        res += '''<listinfo sortfield="%s" sortdirection="%s">\r\n''' % (d['sortfield'], d['sortdirection'])
        for p in d['result_shortlist']:
            if sfields:
                res += '''  <item index="%d" id="%s" type="%s">%s</item>\r\n''' % (p[0], p[1], p[3], u(attr_list_join(p[4])))
            else:
                res += '''  <item index="%d" id="%s" type="%s"/>\r\n''' % (p[0], p[1], p[3])
        res += '''</listinfo>\r\n'''

        xml_timetable = d['timetable'][:]
        xml_timetable.append(['build result xml', time.time() - atime])
        atime = time.time()

        if send_timetable:
            # append info on how long the steps took to get the result
            tt = '<service_handler_process_info>\r\n'
            tt_sum = 0.0
            for i, x in enumerate(xml_timetable):
                tt += '''  <step order="%02d" duration="%.3f" unit="sec." description="%s"/>\r\n''' % (i, x[1], x[0])
                tt_sum += x[1]
            tt += '''  <allsteps durationsum="%.3f" unit="sec."/>\r\n''' % (tt_sum)
            tt += '</service_handler_process_info>\r\n'

            res += tt

    else:
        res += '''<errormessage><![CDATA[%s]]></errormessage>\r\n''' % d['errormessage']

    return escape_illegal_xml_chars(res) + '</response>\r\n'


def struct2template_test(req, path, params, data, d, debug=False, singlenode=False, send_children=False, send_timetable=SEND_TIMETABLE):
    atime = starttime = time.time()
    nodelist = d['nodelist']

    if 'add_shortlist' not in req.params:
        d['result_shortlist'] = []

    d['nodelist'] = [jsonnode.buildNodeDescriptor(req, n, children=send_children) for n in nodelist]
    json_timetable = d['timetable'][:]

    template = req.params.get("template", "record $$[_rcd]$$: id=$$[id]$$: no-template-given\n")
    attrs1 = template.split("$$[")
    attrs = []
    for x in attrs1:
        pos = x.find("]$$")
        if pos >= 0:
            attrs.append(x[0:pos])

    res = ""
    rc = 0  # record count
    for nd in d['nodelist']:
        rc += 1
        x = template
        for attr in attrs:
            if attr == "defaultexport":
                x = x.replace(("$$[%s]$$" % attr), nd[0].get(attr, ''))
            elif attr.startswith("_rc"):
                x = x.replace(("$$[%s]$$" % attr), attr.replace("_rc", "%") % rc)
            elif attr in ["id", "nodename", "nodetype"]:
                x = x.replace(("$$[%s]$$" % attr), nd[0].get(attr.replace("node", ""), ''))
            else:
                x = x.replace(("$$[%s]$$" % attr), nd[0]["attributes"].get(attr, ''))
        res = res + x

    d['timetable'] = []
    if send_timetable:
        d['timetable'] = json_timetable

    d['timetable'] = json_timetable
    d['dataready'] = ("%.3f" % (time.time() - d['build_response_start']))

    res = res.replace("\\n", "\n").replace("\\l", "\l").replace("\\r", "\r").replace("\\t", "\t")

    if 'bom' in params.keys():
        import codecs
        res = codecs.BOM_UTF8 + res

    return res


def struct2json(req, path, params, data, d, debug=False, singlenode=False, send_children=False, send_timetable=SEND_TIMETABLE):
    atime = starttime = time.time()
    nodelist = d['nodelist']

    if 'add_shortlist' not in req.params:
        d['result_shortlist'] = []

    d['nodelist'] = [jsonnode.buildNodeDescriptor(req, n, children=send_children) for n in nodelist]
    json_timetable = d['timetable'][:]

    d['timetable'] = []
    if send_timetable:
        d['timetable'] = json_timetable

    try:
        s = json.dumps(d, indent=4, encoding="UTF-8")
    except:
        s = json.dumps(d, encoding='latin1')

    d['timetable'] = json_timetable
    d['dataready'] = ("%.3f" % (time.time() - d['build_response_start']))
    return s


def struct2csv(req, path, params, data, d, debug=False, sep=';', string_delimiter='"', singlenode=False, send_children=False):

    # delimiter and separator can be transferred by the query
    # this dictionary decodes the characters that would disturb in the url
    trans = {
        'none': u(''),
        'tab': u('\t'),
        'quote': u("'"),
        'dquote': u('"'),
    }

    string_delimiter = u(params.get('delimiter', string_delimiter))
    if string_delimiter.lower() in trans.keys():
        string_delimiter = trans[string_delimiter.lower()]

    sep = u(params.get('sep', sep))
    if sep.lower() in trans.keys():
        sep = trans[sep.lower()]

    def join_row(row):
        row = [u(x) for x in row]

        try:
            if string_delimiter:
                res = string_delimiter + \
                    ((string_delimiter + sep +
                      string_delimiter).join([x.replace(string_delimiter, u("'")) for x in row])) + string_delimiter
            else:
                res = sep.join(row)
        except:
            res = u("")
            for x in row:
                if string_delimiter:
                    x = x.replace(string_delimiter, u("'"))
                try:
                    res += string_delimiter + u(x) + string_delimiter + sep
                except:
                    try:
                        res += string_delimiter + x.decode('utf-8') + string_delimiter + sep
                    except:
                        try:
                            res += string_delimiter + x.decode('latin1') + string_delimiter + sep
                        except:
                            res += string_delimiter + x + string_delimiter + sep
            if res:
                res = res[0:-len(sep)]
        return u(res)

    r = u('')  # string to be returned

    if d['status'].lower() == 'fail':
        header = ['status', 'html_response_code', 'errormessage', 'retrievaldate', 'dataready']
        r = join_row(header) + u('\r\n')
        r += join_row(map(lambda x: u(d[x]), header))
        return u(r)

    rd = {}
    keys = set()
    csv_nodelist = d['nodelist'][:]
    csvattrs = []
    if 'csvattrs' in params:
        csvattrs = [attr.strip() for attr in params['csvattrs'].split(',')]

    for i, n in enumerate(csv_nodelist):
        rd[i] = {}
        rd[i]['id'] = u(n.id)
        rd[i]['name'] = u(n.name)
        rd[i]['type'] = u(n.type)
        attrs = copy.deepcopy(n.attributes)
        rd[i]['attributes'] = attrs
        keys = keys.union(attrs.keys())

    if csvattrs:
        keys = set(csvattrs)

    sorted_tuples = sorted([(x.lower(), x) for x in list(keys)])
    attr_header = [u(x[1]) for x in sorted_tuples]

    # sortfields shall appear early (after id, type and name of the node) of the csv table
    if 'sfields' in d.keys() and d['sfields']:
        for sfield in d['sfields']:
            if sfield in attr_header:
                attr_header.remove(sfield)
        attr_header = d['sfields'] + attr_header

    # filter attribute names
    attr_header = filter(attribute_name_filter, attr_header)

    header = [u('count'), u('id'), u('type'), u('name')] + attr_header
    r = join_row(header) + u('\r\n')

    for i, n in enumerate(csv_nodelist):
        row = [u(i), u(rd[i]['id']), u(rd[i]['type']), u(rd[i]['name'])]
        for attr in attr_header:
            # handle sortfields in attr_header that are not attributes
            if attr in ['node.id', 'node.name', 'node.type']:
                continue
            elif attr in ['node.orderpos']:
                row.append(tree.getNode(rd[i]['id']).get(attr))
            else:
                row.append(u(rd[i]['attributes'].setdefault(attr, '')))
        r += join_row(row) + u('\r\n')

    if 'bom' in params.keys():
        import codecs
        r = codecs.BOM_UTF8 + r
    return u(r)


def struct2rss(req, path, params, data, d, debug=False, singlenode=False, send_children=False):
    atime = starttime = time.time()
    nodelist = d['nodelist']
    language = params.get('lang', 'en')
    items_list = []
    mdts = tree.getRoot("metadatatypes").getChildren()

    for n in nodelist:
        nodename = n.name
        nodeid = n.id
        nodetype = n.type
        updatetime = utime = try_node_date(n)

        # categories to be included in all items - mask generated or not
        default_categories = ''
        if n.type.strip():
            default_categories = '<category>node type: ' + n.type.strip() + '</category>\r\n'

        # check for export mask for this node
        try:
            schema = n.getSchema()
            try:
                mdt = [x for x in mdts if x.name == schema][0]
            except:
                mdt = None
            mask = mdt.getMask('rss')
            if mask.get('masktype') != 'export':
                mask = None
        except:
            mask = None

        if mask:
            item_xml = '<item>\r\n' + mask.getViewHTML([n], flags=8) + default_categories + '\r\n</item>\r\n'
            items_list = items_list + [(updatetime, nodename, nodeid, item_xml)]
            continue

        # no rss export mask: build default item from nodesmall mask
        item_d = {}

        browsingPathList = getBrowsingPathList(n)
        browsingPathList = [x for x in browsingPathList if (guestAccess.hasAccess(x[-1], 'read') and (isDescendantOf(x[-1], collections)))]
        browsingPathList_names = [map(lambda x: x.name, browsingPath) for browsingPath in browsingPathList]

        # assumption: longest path is most detailled and illustrative for being used in the title
        x = sorted([[len(p), i, p] for i, p in enumerate(browsingPathList_names)])
        x.reverse()
        try:
            most_detailed_path = x[0][2]
        except:  # browsing path list may be empty (for directories, collections, ...)
            most_detailed_path = ''

        if nodename:
            item_d['title'] = esc(nodename + ' (' + nodeid + ', ' + nodetype + ') ' + ('/'.join(most_detailed_path)))
        else:
            item_d['title'] = esc('-unnamed-node-' + ' (' + nodeid + ', ' + nodetype + ') ' + ('/'.join(most_detailed_path)))

        item_d['item_pubDate'] = utime
        item_d['guid'] = host + '/node?id=%s' % str(nodeid)
        item_d['link'] = host + '/node?id=%s' % str(nodeid)

        mtype = getMetaType(n.getSchema())

        if mtype:
            lang_masks = [m for m in mtype.getMasks() if m.getLanguage() == language and m.name.startswith('nodesmall')]
            if lang_masks:
                mask = lang_masks[0]
            else:
                mask = mtype.getMask('nodesmall')
            attr_list = mask.getViewHTML([n], VIEW_DATA_ONLY, language)  # [[attr_name, value, label, type], ...]
        else:
            attr_list = [['', str(n.id), 'node id', ''], ['', n.name, 'node name', ''], ['', n.type, 'node type', ''], ]

        description = ''
        for x in attr_list:
            description = description + ('''<b>%s: </b>%s<br/>\r\n''' % (u(x[2]), (x[1])))

        item_d['description'] = description
        categories = default_categories

        for x in browsingPathList_names:
            categories = categories + '<category>' + esc('/'.join(x)) + '</category>\r\n'

        ddcs = n.get('ddc').strip()
        if ddcs.strip():
            ddcs = ddcs.split(';')
            for ddc in ddcs:
                categories = categories + '<category>' + esc(ddc) + '</category>\r\n'

        subjects = n.get('subject').strip()
        if subjects:
            subjects = subjects.split(';')
            for subject in subjects:
                categories = categories + '<category>' + esc(u2(subject)) + '</category>\r\n'

        item_d['categories'] = categories

        for k, v in item_d.items():
            item_d[k] = u(v)

        items_list = items_list + [(updatetime, nodename, nodeid, (template_rss_item % item_d))]

    if items_list:
        items_list.sort()
        items_list.reverse()

    items = ''
    for x in items_list:
        items += (x[3] + '\r\n')

    pubDate = lastBuildDate = format_date(format='rfc822')

    d['dataready'] = ("%.3f" % (time.time() - d['build_response_start']))

    fcd = feed_channel_dict.copy()
    fcd['lang'] = 'de'
    fcd['pubdate'] = pubDate
    fcd['lastbuild'] = lastBuildDate
    fcd['link'] = host
    fcd['atom_link'] = host + req.fullpath
    fcd['image_title'] = 'testlogo'
    fcd['image_link'] = host + '/img/testlogo.png'
    fcd['image_url'] = host + '/img/testlogo.png'

    if 'feed_info' in params:
        for k, v in params['feed_info'].items():
            fcd[k] = v
    else:
        fcd['title'] = host + req.fullpath + str(req.query)
    fcd['items'] = items
    s = template_rss_channel % fcd  # params['feed_info']

    return s

supported_formats = [
    [['xml', ''], struct2xml, 'text/xml'],
    [['json'], struct2json, 'text/plain'],
    [['csv'], struct2csv, 'text/plain'],
    [['template_test'], struct2template_test, 'text/plain'],
    [['rss'], struct2rss, 'application/rss+xml'],
]


def get_node_children_struct(
        req, path, params, data, id, debug=True, allchildren=False, singlenode=False, parents=False, send_children=False):
    global guestAccess
    atime = starttime = time.time()
    retrievaldate = format_date()

    res = {}  # holds the resulting data structure
    res['build_response_start'] = starttime
    res['retrievaldate'] = retrievaldate
    res['method'] = req.command
    res['path'] = req.path
    res['query'] = req.query
    timetable = []
    res['timetable'] = timetable

    res['oauthuser'] = ''  # username supplied for authentication (login name) in query parameter user
    res['userid'] = ''  # unique id for authenticated user if applicable (node.id for internal, dirid for dynamic users)
    res['username'] = ''  # name of the user, may be "guest" or personal name

    # verify signature if a user is given, otherwise use guest user
    if params.get('user'):
        _username = params.get('user')
        res['oauthuser'] = _username
        _user = users.getUser(_username)

        if not _user:  # user of dynamic type and not logged in with this request

            timetable.append(
                [
                    '''oauth: users.getUser(%r) returned %r: going to built dummy user with attributes of homedir with system.oauthuser=%r''' %
                    (_username, _user, _username), time.time() - atime])
            atime = time.time()

            dirid = _username

            # build an object with attributes used by AccessData constructor
            class dummyuser:  # dummy user class

                def __init__(self, dirid):
                    self.dirid = dirid

                    # find home directory for dynamic user with given directory id
                    self.homedir = None
                    self.usertype = ''
                    for hd in tree.getRoot("home").getChildren():
                        if hd.get('system.oauthuser') == dirid:
                            self.homedir = hd
                            items = hd.items()
                            for k, v in items:
                                if k.startswith('system.dirid.') and v == dirid:
                                    self.usertype = k.replace('system.dirid.', '')
                                    break
                            break

                    self.dirgroups = []
                    if self.homedir:
                        self.dirgroups = self.homedir.get('system.dirgroups.' + self.usertype)
                        if not self.dirgroups:
                            self.dirgroups = ''
                        self.dirgroups = self.dirgroups.split('|#|')
                        self.name = self.homedir.get('system.name.' + self.usertype)
                        self.last_authentication = self.homedir.get('system.last_authentication.' + self.usertype)
                    else:
                        self.name = self.dirid

                    self.groups = [
                        g.name for g in tree.getRoot('usergroups').getChildren() if (
                            g.get('allow_dynamic') == '1' and params.get('user') in g.get('dynamic_users')) or g.name in self.dirgroups]

                    self.is_admin = config.get("user.admingroup", "Administration") in self.groups

                def getGroups(self):  # return all groups with given dynamic user
                    return self.groups

                def getName(self):
                    return self.name

                def getUserID(self):  # unique identifier
                    return self.dirid

                def getUserType(self):
                    return 'dummy_' + self.usertype

                def isAdmin(self):
                    return self.is_admin

            _user = dummyuser(dirid)
            homedir = _user.homedir
            if homedir:
                timetable.append(['''oauth: built dummy dyn. user %r, homedir: %r %r -> groups: %r''' %
                                  (_username, homedir.name, homedir.id, _user.getGroups()), time.time() - atime])
                atime = time.time()
            else:
                timetable.append(['''oauth: tried to built dummy dyn. user %r, no homedir found''' % (_username), time.time() - atime])
                atime = time.time()

        else:
            # users.getUser(_username) returned user
            timetable.append(['''oauth: users.getUser(%r) returned %r (%r, %r, %r) -> groups: %r''' %
                              (_username, _user, _user.getName(), _user.getUserID(), _user.getUserType(), _user.getGroups()), time.time() -
                              atime])
            atime = time.time()

        guestAccess = AccessData(user=_user)

        if guestAccess.user:
            valid = guestAccess.verify_request_signature(req.fullpath, params)
            if not valid:
                guestAccess = None
            else:
                res['userid'] = _user.getUserID()
            timetable.append(['''oauth: verify_request_signature returned %r for authname %r, userid: %r, groups: %r''' %
                              (valid, _username, res['userid'], _user.getGroups()), time.time() - atime])
            atime = time.time()
        else:
            guestAccess = None
    else:
        guestAccess = AccessData(user=users.getUser('Gast'))

    if guestAccess:
        res['username'] = guestAccess.getUser().getName()  # name,
        res['userid'] = guestAccess.getUser().getUserID()  # id,
    result_shortlist = []

    nodelist = []
    res['nodelist'] = nodelist

    # query parameters
    nodelist_type = params.get('type', '')  # return only nodes of given type like dissertation/diss
    parent_type = params.get('parent_type', '')  # return only nodes that have only parents of  given type like folder or collection
    send_versions = params.get('send_versions', '').lower()  # return also nodes that are older versions of other nodes
    # return only nodes that have an EXIF location that lies between the given lon,lat values
    exif_location_rect = params.get('exif_location_rect', '')
    mdt = params.get('mdt', '')
    attrreg = params.get('attrreg', '')
    q = params.get('q', '')  # node query
    sortfield = params.get('sortfield', '')
    sortformat = params.get('sortformat', '')  # 'sissfi'
    sfields = []  # sortfields

    if sortfield:
        sfields = [x.strip() for x in sortfield.split(',')]
    num_sfields = len(sfields)

    sortdirection = ''
    for i in range(num_sfields):
        if sfields[i] and sfields[i][0] == '-':
            sfields[i] = sfields[i][1:]
            sortdirection += 'd'
        else:
            sortdirection += 'u'

    psort = params.get('sort', 'orderpos')
    sortresult = ''

    default_nodelist_start = 0
    default_nodelist_limit = 100

    res['timetable'] = timetable

    try:
        nodelist_start = int(params.get('start', default_nodelist_start))
    except:
        nodelist_start = default_nodelist_start

    try:
        nodelist_limit = int(params.get('limit', default_nodelist_limit))
    except:
        nodelist_limit = default_nodelist_limit

    if singlenode:
        nodelist_start = 0
        nodelist_limit = 1

    # accept results calculated and cached up to this amount of seconds
    acceptcached = float(params.get('acceptcached', '0'))

    # check node existence
    try:
        node = tree.getNode(id)
    except:
        res['status'] = 'fail'
        res['html_response_code'] = '404'  # not found
        res['errormessage'] = 'node not found'
        res['build_response_end'] = time.time()
        dataready = "%.3f" % (res['build_response_end'] - starttime)
        res['dataready'] = dataready
        return res

    # check node access
    if guestAccess is not None and guestAccess.hasAccess(node, "read") and (
            isDescendantOf(node, collections) or isDescendantOf(node, home)):
        pass
    else:
        res['status'] = 'fail'
        res['html_response_code'] = '403'  # forbidden (authorization will not help)
        res['errormessage'] = 'no access'
        res['build_response_end'] = time.time()
        dataready = "%.3f" % (res['build_response_end'] - starttime)
        res['dataready'] = dataready
        return res

    atime = time.time()
    searchresult = []
    if q:
        cache_key = (path).split('?')[0] + '|q=' + q  # req.path
        resultcode, cachecontent = searchcache.retrieve(cache_key, acceptcached)
        if resultcode == 'hit':
            time_cached = searchcache.getTimestamp(cache_key)
            time_delta = starttime - time_cached
            searchresult = cachecontent[-1]
            timetable.append(['retrieved filtered search result from cache: %d nodes, time_delta: %.3f lower acceptcached %.3f sec.' % (
                len(searchresult), time_delta, acceptcached), time.time() - atime])
            atime = time.time()
        elif resultcode == 'refused':
            time_cached = searchcache.getTimestamp(cache_key)
            time_delta = starttime - time_cached
            timetable.append(['cached filtered search result exists, but not used: time_delta: %.3f sec. higher acceptcached %.3f sec.' % (
                time_delta, acceptcached), time.time() - atime])
            atime = time.time()

        if resultcode != 'hit':
            searchresult = node.search(q)
            timetable.append(['execute search q=%s on node (%s, %s, %s) resulting in %d nodes' %
                              (q, node.id, node.type, node.name, len(searchresult)), time.time() - atime])
            atime = time.time()
            searchresult = guestAccess.filter(searchresult)
            timetable.append(['filter access for search result resulting in %d nodes' % (len(searchresult)), time.time() - atime])
            atime = time.time()
            if acceptcached > 0:  # only write to cache for these requests
                searchcache.update(cache_key, searchresult)
                timetable.append(['wrote filtered search result to cache (%d nodes), now in cache: %d entries: %s' %
                                  (len(searchresult), searchcache.getKeysCount(), "#".join(searchcache.getKeys())), time.time() - atime])
                atime = time.time()

    res['timetable'] = timetable
    typed_nodelist = []
    if mdt:
        mdt_names = [x.name for x in tree.getRoot("metadatatypes").getChildren()]
        if mdt not in mdt_names:
            res['status'] = 'fail'
            res['html_response_code'] = '404'  # not found
            res['errormessage'] = 'no such metadata type: ' + mdt
            res['build_response_end'] = time.time()
            dataready = "%.3f" % (res['build_response_end'] - starttime)
            res['dataready'] = dataready
            return res
        from core.db import database
        db = database.getConnection()
        typed_node_id_list = db.get_nids_by_type_suffix(mdt)
        db.close()
        if typed_node_id_list:
            typed_nodelist = tree.NodeList(typed_node_id_list)
            timetable.append(['''generated typed node list -> (%d nodes)''' % (len(typed_nodelist)), time.time() - atime])
            atime = time.time()

    if singlenode:
        nodelist = [node]
    elif parents:
        nodelist = node.getParents()
        timetable.append(['''get parents for node %s, '%s', '%s' -> (%d nodes)''' %
                          (str(node.id), node.name, node.type, len(nodelist)), time.time() - atime])
        atime = time.time()
    elif allchildren:
        if q and not mdt:
            nodelist = searchresult
        elif mdt and not q:
            if typed_nodelist:
                nodelist = tree.NodeList([x for x in typed_nodelist if (guestAccess.hasAccess(x, 'read') and (isDescendantOf(x, node)))])
                timetable.append(['''access filter of typed (%s) nodes -> (%d nodes)''' % (mdt, len(nodelist)), time.time() - atime])
                atime = time.time()
        elif mdt and q:
            filtered_nodelist = tree.NodeList(
                [x for x in typed_nodelist if (guestAccess.hasAccess(x, 'read') and (isDescendantOf(x, node)))])
            timetable.append(['''access filter of typed (%s) nodes -> (%d nodes)''' % (mdt, len(nodelist)), time.time() - atime])
            atime = time.time()
            nodelist = intersection([filtered_nodelist, searchresult])
            timetable.append(['''intersection of typed (%s) nodes with searchresult -> (%d nodes)''' %
                              (mdt, len(nodelist)), time.time() - atime])
            atime = time.time()
        else:
            # refuse request for all children on collections root
            if node.id != tree.getRoot('collections').id:
                nodelist = node.getAllChildren()
            else:
                nodelist = []
                res['status'] = 'fail'
                res['html_response_code'] = '403'  # forbidden (authorization will not help)
                res['errormessage'] = 'no access'
                res['build_response_end'] = time.time()
                dataready = "%.3f" % (res['build_response_end'] - starttime)
                res['dataready'] = dataready
                res['timetable'] = timetable
                return res
            timetable.append(['''get all children for node %s, '%s', '%s' -> (%d nodes)''' %
                              (str(node.id), node.name, node.type, len(nodelist)), time.time() - atime])
            atime = time.time()
    else:
        nodelist = node.getChildren()
        timetable.append(['''get direct children for node %s, '%s', '%s' -> (%d nodes)''' %
                          (str(node.id), node.name, node.type, len(nodelist)), time.time() - atime])
        atime = time.time()
        if q:
            nodelist = intersection([searchresult, nodelist])
            timetable.append(['''searchresult filter with direct children for node %s, '%s', '%s' -> (%d nodes)''' %
                              (str(node.id), node.name, node.type, len(nodelist)), time.time() - atime])
            atime = time.time()
        if mdt:
            nodelist = intersection([typed_nodelist, nodelist])
            timetable.append(['''filter typed nodes with direct children for node %s, '%s', '%s' -> (%d nodes)''' %
                              (str(node.id), node.name, node.type, len(nodelist)), time.time() - atime])
            atime = time.time()

    req_path = req.path

    # if type(nodelist)!= list:
    #    set_nodelist_ids = set(nodelist.getIDs())
    # else:
    #    set_nodelist_ids = set(nodelist)

    set_nodeid_localread = set(["%s_%s" % (str(n.id), str(n.localread)) for n in nodelist])

    timetable.append(['get set of ids of nodelist', time.time() - atime])
    atime = time.time()

    try:
        from core.acl import getDefaultGuestAccessRule
        default_guest_access_name = getDefaultGuestAccessRule().name
    except:
        default_guest_access_name = None

    if not default_guest_access_name:
        logger.warning('No default guest access name set in config file: will use hasAccess method, which may cost web service performance')

    if not mdt and not q:
        resultcode, cachecontent = filtercache.retrieve(req_path)
        if resultcode == 'hit' and len(set_nodeid_localread.difference(cachecontent[-1][0])) == 0:
            filtered_nodelist = cachecontent[-1][1]
            timetable.append(['retrieved filtered access from cache (%d nodes -> %d nodes)' %
                              (len(nodelist), len(filtered_nodelist)), time.time() - atime])
            atime = time.time()
            nodelist = filtered_nodelist
        elif not q:

            if 0 and default_guest_access_name:
                filtered_nodelist = [x for x in nodelist if default_guest_access_name in x.localread.split(',')]
                timetable.append(['filter access with localread == "%s" (%d nodes -> %d nodes)' %
                                  (default_guest_access_name, len(nodelist), len(filtered_nodelist)), time.time() - atime])
                atime = time.time()
            else:
                if singlenode or parents:
                    filtered_nodelist = [x for x in nodelist if (guestAccess.hasAccess(x, 'read'))]
                else:
                    filtered_nodelist = [x for x in nodelist if (guestAccess.hasAccess(x, 'read'))]
                timetable.append(['filter access with hasAccess (%d nodes -> %d nodes)' %
                                  (len(nodelist), len(filtered_nodelist)), time.time() - atime])
                atime = time.time()

            nodelist = filtered_nodelist

            if not singlenode and len(filtered_nodelist) > FILTERCACHE_NODECOUNT_THRESHOLD:
                filtercache.update(req_path, [set_nodeid_localread, filtered_nodelist])
                timetable.append(['added filtered nodelist to filtercache (%d nodes)' % (len(filtered_nodelist)), time.time() - atime])
                atime = time.time()

    # 'sort' may be removed later (undocumented feature)
    if not singlenode and 'sort' in params.keys():
        # sort default with orderpos
        nodelist = tree.NodeList(nodelist)
        nodelist = nodelist.sort(psort)
        timetable.append(["sort nodelist (%d nodes): sort='%s'" % (len(nodelist), psort), time.time() - atime])
        atime = time.time()

    if nodelist_type:
        stypes = [x.strip() for x in nodelist_type.split(',')]
        typefiltered_nodelist = []
        for stype in stypes:
            try:
                regexp_stype = re.compile(stype)
            except:
                res['status'] = 'fail'
                res['html_response_code'] = '403'  # not found
                res['errormessage'] = "invalid expression '%s' in parameter '%s'" % (stype, 'type')
                res['build_response_end'] = time.time()
                dataready = "%.3f" % (res['build_response_end'] - starttime)
                res['dataready'] = dataready
                res['timetable'] = timetable
                return res

            newly_filtered = [x for x in nodelist if regexp_stype.match(x.type)]
            typefiltered_nodelist += newly_filtered
            timetable.append(['filter node type %s (-> %d nodes)' % (stype, len(newly_filtered)), time.time() - atime])
            atime = time.time()
        nodelist = tree.NodeList(list(set(typefiltered_nodelist)))
        timetable.append(['built set from type filter results (total: %d nodes)' % (len(nodelist)), time.time() - atime])
        atime = time.time()

    if parent_type:
        # filter all nodes with parents that are not of one of the specified types
        typefiltered_nodelist = []
        for stype in [x.strip() for x in parent_type.split(',')]:
            try:
                regexp_stype = re.compile(stype)
            except:
                res['status'] = 'fail'
                res['html_response_code'] = '403'  # not found
                res['errormessage'] = "invalid expression '%s' in parameter '%s'" % (stype, 'type')
                res['build_response_end'] = time.time()
                dataready = "%.3f" % (res['build_response_end'] - starttime)
                res['dataready'] = dataready
                res['timetable'] = timetable
                return res

            newly_filtered = []  # [x for x in nodelist if regexp_stype.match(x.type)]

            for one_node in nodelist:
                parents_comply = True
                for one_parent in one_node.getParents():
                    if regexp_stype.match(one_parent.type):
                        pass
                    else:
                        parents_comply = False
                        break

                if parents_comply:
                    newly_filtered.append(one_node)

            typefiltered_nodelist += newly_filtered
            timetable.append(['filter parent type %s (-> %d nodes)' % (stype, len(newly_filtered)), time.time() - atime])
            atime = time.time()
        nodelist = tree.NodeList(list(set(typefiltered_nodelist)))
        timetable.append(['built set from type filter results (total: %d nodes)' % (len(nodelist)), time.time() - atime])
        atime = time.time()

    if send_versions in ["1"]:
        pass
    else:
        # this is the default: remove older version nodes from the result list
        nodelist = [n for n in nodelist if n.isActiveVersion() or n.id == n.next_nid]
        timetable.append(['filtered older (inactive) versions out -> (%d nodes)' % (len(nodelist)), time.time() - atime])
        atime = time.time()

    if exif_location_rect:
        # filter all nodes that have an EXIF location inside the given rectangle
        components = exif_location_rect.split(',')

        if len(components) != 4:
            res['status'] = 'fail'
            res['html_response_code'] = '403'  # not found
            res['errormessage'] = "invalid expression '%s' in parameter '%s'" % (stype, 'type')
            res['build_response_end'] = time.time()
            dataready = "%.3f" % (res['build_response_end'] - starttime)
            res['dataready'] = dataready
            res['timetable'] = timetable
            return res

        typefiltered_nodelist = []

        for one_node in nodelist:
            location = one_node.get_location()
            if "lon" in location and "lat" in location:
                node_lon = location["lon"]
                node_lat = location["lat"]

                test_lat_lower = float(components[0])
                test_lon_lower = float(components[1])
                test_lat_upper = float(components[2])
                test_lon_upper = float(components[3])

                if node_lon > test_lon_lower and node_lon < test_lon_upper and node_lat > test_lat_lower and node_lat < test_lat_upper:
                    typefiltered_nodelist.append(one_node)

        timetable.append(['filter exif location rect %s (-> %d nodes)' %
                          (exif_location_rect, len(typefiltered_nodelist)), time.time() - atime])
        atime = time.time()
        nodelist = tree.NodeList(list(set(typefiltered_nodelist)))
        timetable.append(['built set from type filter results (total: %d nodes)' % (len(nodelist)), time.time() - atime])
        atime = time.time()

    if attrreg:
        attrreg_filtered_nodelist = []
        try:
            akey, aval = attrreg.split('=')
            regexp_attrreg = re.compile(aval)
        except:
            res['status'] = 'fail'
            res['html_response_code'] = '403'  # not found
            res['errormessage'] = "invalid expression '%s' in parameter '%s'" % (attrreg, 'attrreg')
            res['build_response_end'] = time.time()
            dataready = "%.3f" % (res['build_response_end'] - starttime)
            res['dataready'] = dataready
            res['timetable'] = timetable
            return res

        attrreg_filtered_nodelist += [x for x in nodelist if regexp_attrreg.match(x.get(akey))]
        timetable.append(['filter attrreg %s (-> %d nodes)' % (attrreg, len(attrreg_filtered_nodelist)), time.time() - atime])
        atime = time.time()
        nodelist = tree.NodeList(list(set(attrreg_filtered_nodelist)))

    if sortfield:
        def reformat(inputlist, i, f):
            '''the i.th column in a list of list  is formated (i.e. from string to integer, float, ...'''
            for t in inputlist:
                t[i] = f(t[i])
            return inputlist

        def nodeValueGetter(node, valuename):
            '''get node related values in uniform fashion: like 'node.id', 'node.name', 'node.type', 'orderpos', attributes'''
            if valuename.startswith('node.'):
                if valuename == 'node.id':
                    return node.id
                elif valuename == 'node.name':
                    return node.name
                elif valuename == 'node.type':
                    return node.type
                elif valuename == 'node.orderpos':
                    return node.orderpos
            else:
                return node.get(valuename)

        nodetuples = [map(lambda sfield: nodeValueGetter(x, sfield), sfields) + [x.id, x] for x in nodelist]

        data = nodetuples[:]

        for i in range(num_sfields):
            pos = num_sfields - i - 1

            fReverse = False  # default
            try:
                field_sortdirection = sortdirection[pos]
                if field_sortdirection == 'u':
                    fReverse = False
                elif field_sortdirection == 'd':
                    fReverse = True
                else:
                    # perhaps return "failed" in this case ?
                    pass
            except:
                pass

            def int_getter(pos, x):
                try:
                    return int(float(x[pos]))
                except:
                    return 0

            def float_getter(pos, x):
                try:
                    return float(x[pos])
                except:
                    return 0.0

            # map formats for sortfield (defaul: string)
            sortkey = lambda x: serviceutils.din5007v2(x[pos])
            try:
                field_format = sortformat[pos]
                if field_format == 'i':
                    sortkey = lambda x: int_getter(pos, x)
                # XXX: this was 'fieldformat' before, recheck!
                elif field_format == 'f':
                    sortkey = lambda x: float_getter(pos, x)
                else:
                    pass
            except:
                pass

            data = sorted(data, key=sortkey, reverse=fReverse)

        nodetuples = data[:]
        nodelist = [x[len(sfields) + 1] for x in nodetuples]  # sorted
        timetable.append(["sort nodelist (%d nodes): sortfield='%s', sortdirection='%s', sortformat='%s'" %
                          (len(nodelist), sortfield, sortdirection, sortformat), time.time() - atime])
        atime = time.time()
        res['timetable'] = timetable

    nodelist_countall = len(nodelist)

    def attr_list(node, sfields):
        r = []
        for sfield in sfields:
            r.append([sfield, node.get(sfield)])
        return r

    i0 = int(params.get('i0', '0'))
    i1 = int(params.get('i1', len(nodelist)))

    if 'add_shortlist' in req.params:
        if sortfield:
            result_shortlist = [[i, x.id, x.name, x.type, attr_list(x, sfields)] for i, x in enumerate(nodelist)][i0:i1]
            timetable.append(['build result_shortlist for %d nodes and %d sortfields' %
                              (len(result_shortlist), len(sfields)), time.time() - atime])
            atime = time.time()
        else:
            result_shortlist = [[i, x.id, x.name, x.type] for i, x in enumerate(nodelist)][i0:i1]
            timetable.append(['build result_shortlist for %d nodes (no sortfield)' % len(result_shortlist), time.time() - atime])
            atime = time.time()

    if 'limit' in params:
        nodelist = nodelist[nodelist_start:nodelist_start + nodelist_limit]
    else:
        nodelist = nodelist[nodelist_start:]

    res['nodelist'] = nodelist
    res['sfields'] = sfields
    res['sortfield'] = sortfield
    res['sortdirection'] = sortdirection
    res['result_shortlist'] = result_shortlist
    res['timetable'] = timetable[:]
    res['nodelist_start'] = nodelist_start
    res['nodelist_limit'] = nodelist_limit
    res['nodelist_countall'] = nodelist_countall
    res['path'] = req.path
    res['status'] = 'ok'
    res['html_response_code'] = '200'  # ok
    res['build_response_end'] = time.time()
    dataready = "%.3f" % (res['build_response_end'] - starttime)
    res['dataready'] = dataready
    return res


def write_formatted_response(
        req, path, params, data, id, debug=True, allchildren=False, singlenode=False, parents=False, send_children=False):

    atime = starttime = time.time()
    r_timetable = []

    _p = params.copy()
    if "jsoncallback" in _p:
        del _p['jsoncallback']
    if "_" in _p:
        del _p['_']

    cache_key = '|'.join(map(str, [path, _p, allchildren, singlenode, parents, send_children]))
    cache_key = cache_key.replace(' ', '_')

    acceptcached = float(params.get('acceptcached', '0'))

    result_from_cache = None
    if acceptcached > 0.0:
        resultcode, cachecontent = resultcache.retrieve(cache_key, acceptcached)
        if resultcode == 'hit':
            cache_name = 'resultcache'
            timestamp_from_cache = time_cached = resultcache.getTimestamp(cache_key)
            time_delta = starttime - time_cached
            result_from_cache, mimetype_from_cache = cachecontent[-1]
            # replace jQuery, jsonp callback value
            if result_from_cache.startswith('jQuery') or result_from_cache.startswith('jsonp'):
                result_from_cache = str(params['jsoncallback']) + result_from_cache[result_from_cache.find("({"):]

            r_timetable.append(["retrieved filtered result from 'resultcache': (%d bytes), time_delta: %.3f lower acceptcached %.3f sec." % (
                len(result_from_cache), time_delta, acceptcached), time.time() - atime])
            atime = time.time()
        elif resultcode == 'refused':
            time_cached = resultcache.getTimestamp(cache_key)
            time_delta = starttime - time_cached
            r_timetable.append(["cached result exists in 'resultcache', but not used: time_delta: %.3f sec. higher acceptcached %.3f sec." % (
                time_delta, acceptcached), time.time() - atime])
            atime = time.time()

    if not result_from_cache:

        d = get_node_children_struct(req, path, params, data, id, debug=debug, allchildren=allchildren,
                                     singlenode=singlenode, send_children=send_children, parents=parents)

        if r_timetable:
            d['timetable'] = r_timetable + d.setdefault('timetable', [])
            r_timetable = []

        res_format = (params.get('format', 'xml')).lower()
        formatIsSupported = False

        mimetype = ''

        for supported_format in supported_formats:
            if res_format in supported_format[0]:
                atime = time.time()
                formatIsSupported = True
                s = supported_format[1](req, path, params, data, d, debug=debug, singlenode=singlenode, send_children=send_children)
                if res_format == 'json' and 'jsoncallback' in params:
                    s = params['jsoncallback'] + '(' + s + ')'
                mimetype = params.get('mimetype', supported_format[2])
                req.reply_headers['Content-Type'] = mimetype + "; charset=utf-8"
                d['timetable'].append(["formatted for '%s'" % res_format, time.time() - atime])
                atime = time.time()

                disposition = req.params.get('disposition', '')
                if disposition:
                    # ex.: (direct to download) value: "attachment; filename=myfilename.txt"
                    # ex.: (open in browser) value: "filename=myfilename.txt"
                    req.reply_headers['Content-Disposition'] = disposition
                    d['timetable'].append(["wrote disposition %r to reply header" % (disposition), time.time() - atime])
                    atime = time.time()

                break

        if not formatIsSupported:
            d['status'] = 'fail'
            d['html_response_code'] = '404'  # not found
            d['errormessage'] = 'unsupported format'
            d['build_response_end'] = time.time()

            s = struct2xml(req, path, params, data, d, singlenode=True, send_children=False)
            req.reply_headers['Content-Type'] = "text/xml; charset=utf-8"

        if acceptcached > 0:  # only write to cache for these requests
            resultcache.update(cache_key, [s, mimetype])
            d['timetable'].append(["wrote result to 'resultcache' (%d bytes), now in cache: %d entries" %
                                   (len(s), resultcache.getKeysCount()), time.time() - atime])
            atime = time.time()
            #d['timetable'].append(["wrote result to 'resultcache' (%d bytes), now in cache: %d entries: \r\n%s" % (len(s), resultcache.getKeysCount(), resultcache.report()), time.time()-atime]); atime = time.time()
            # d['timetable'].append(["wrote result to 'resultcache' (%d bytes), now in
            # cache: %d entries: %s" % (len(s), resultcache.getKeysCount(),
            # "#".join(resultcache.getKeys())), time.time()-atime]); atime =
            # time.time()

        s = modify_tex(s, 'strip')

    else:
        d = {}
        d['status'] = 'ok'
        d['html_response_code'] = '200'  # ok
        d['build_response_end'] = time.time()
        if r_timetable:
            d['timetable'] = r_timetable[:]
        s = result_from_cache
        d['timetable'].append(["serving %.3f sec. old response (%d bytes) from '%s', cache_key: %s" %
                               (time.time() - timestamp_from_cache, len(s), cache_name, cache_key), time.time() - atime])
        atime = time.time()
        req.reply_headers['Content-Type'] = mimetype_from_cache + "; charset=utf-8"
        mimetype = mimetype_from_cache

    def compressForDeflate(s):
        import gzip
        return gzip.zlib.compress(s, 9)

    def compressForGzip(s):
        import cStringIO
        import gzip
        buffer = cStringIO.StringIO()
        gzfile = gzip.GzipFile(mode='wb', fileobj=buffer, compresslevel=9)
        gzfile.write(s)
        gzfile.close()
        return buffer.getvalue()

    if 'deflate' in req.params:
        size_uncompressed = len(s)
        compressed_s = compressForDeflate(s)
        s = compressed_s
        size_compressed = len(s)
        try:
            percentage = 100.0 * size_compressed / size_uncompressed
        except:
            percentage = 100.0
        req.reply_headers['Content-Encoding'] = "deflate"
        d['timetable'].append(["'deflate' in request: executed compressForDeflate(s), %d bytes -> %d bytes (compressed to: %.1f %%)" %
                               (size_uncompressed, size_compressed, percentage), time.time() - atime])
        atime = time.time()

    elif 'gzip' in req.params:
        size_uncompressed = len(s)
        compressed_s = compressForGzip(s)
        s = compressed_s
        size_compressed = len(s)
        try:
            percentage = 100.0 * size_compressed / size_uncompressed
        except:
            percentage = 100.0
        req.reply_headers['Content-Encoding'] = "gzip"
        d['timetable'].append(["'gzip' in request: executed compressForGzip(s), %d bytes -> %d bytes (compressed to: %.1f %%)" %
                               (size_uncompressed, size_compressed, percentage), time.time() - atime])
        atime = time.time()

    req.reply_headers['Content-Length'] = len(s)

    # (format) Expires: Mon, 28 Nov 2011 12:41:22 GMT
    # see core.athana.build_http_date
    # req.reply_headers['Expires'] = time.strftime ('%a, %d %b %Y %H:%M:%S GMT', time.gmtime(time.time()+60.0)) # 1 minute

    # remark: on 2011-12-01 switched response from req.write to req.sendAsBuffer for performance reasons
    # (before: ) req.write(s)
    req.sendAsBuffer(s, mimetype, force=1)
    d['timetable'].append(["executed req.sendAsBuffer, %d bytes, mimetype='%s'" % (len(s), mimetype), time.time() - atime])
    atime = time.time()
    return d['html_response_code'], len(s), d


def get_node_single(req, path, params, data, id):

    res_children = params.get('children', False)
    if res_children and res_children.lower() not in ['0', 'none', 'false']:
        send_children = True
    else:
        send_children = False

    return write_formatted_response(req, path, params, data, id, debug=True, singlenode=True, send_children=send_children)


def get_node_children(req, path, params, data, id):
    return write_formatted_response(req, path, params, data, id, debug=True, singlenode=False, allchildren=False)


def get_node_allchildren(req, path, params, data, id):
    return write_formatted_response(req, path, params, data, id, debug=True, singlenode=False, allchildren=True)


def get_node_parents(req, path, params, data, id):
    return write_formatted_response(req, path, params, data, id, debug=True, singlenode=False, parents=True)


def get_cachestatus(req, path, params, data):
    atime = time.time()
    timetable = []
    d = {}
    d['status'] = 'ok'
    d['html_response_code'] = '200'
    d['timetable'] = timetable
    req.reply_headers['Content-Type'] = "text/plain" + "; charset=utf-8"

    s = 'searchcache content: %s\r\n' % cache_date2string(time.time(), '%04d-%02d-%02d-%02d-%02d-%02d')
    s += searchcache.report()
    d['timetable'].append(["retrieved report for searchcache", time.time() - atime])
    atime = time.time()

    s += '\r\n\r\nfiltercache content: %s\r\n' % cache_date2string(time.time(), '%04d-%02d-%02d-%02d-%02d-%02d')
    s += filtercache.report()
    d['timetable'].append(["retrieved report for filtercache", time.time() - atime])
    atime = time.time()

    s += '\r\n\r\nresultcache content: %s\r\n' % cache_date2string(time.time(), '%04d-%02d-%02d-%02d-%02d-%02d')
    s += resultcache.report()
    d['timetable'].append(["retrieved report for resultcache", time.time() - atime])
    atime = time.time()

    req.write(s)

    d['timetable'].append(["writing cache reports to request", time.time() - atime])
    atime = time.time()
    return d['html_response_code'], len(s), d


def get_maskcachestatus(req, path, params, data):
    atime = time.time()
    from contenttypes.default import get_maskcache_report
    timetable = []
    d = {}
    d['status'] = 'ok'
    d['html_response_code'] = '200'
    d['timetable'] = timetable
    req.reply_headers['Content-Type'] = "text/plain" + "; charset=utf-8"

    s = 'mask cache content (lookup keys): %s\r\n\r\n' % cache_date2string(time.time(), '%04d-%02d-%02d-%02d-%02d-%02d')

    s += get_maskcache_report()

    req.write(s)
    d['timetable'].append(["writing masks cache access counts to request", time.time() - atime])
    atime = time.time()
    return d['html_response_code'], len(s), d

# alternative base dir for static html files
#
# relative to mediatum folder:
# WEBROOT="./web/services/static01/files/"
#
# absolute:
# WEBROOT="/tmp/"

# WEBROOT="./web/services/static01/files/"

# no WEBROOT configured, default will be used
WEBROOT = None


def serve_file(req, path, params, data, filepath):
    atime = starttime = time.time()

    d = {}
    d['timetable'] = []

    if 'mimetype' in req.params:
        mimetype = req.params['mimetype']
    elif filepath.lower().endswith('.html') or filepath.lower().endswith('.htm'):
        mimetype = 'text/html'
    else:
        mimetype = getMimeType(filepath)

    req.reply_headers['Content-Type'] = mimetype

    if WEBROOT:
        basedir = WEBROOT
    else:
        basedir = os.path.dirname(os.path.abspath(__file__))
    abspath = os.path.join(basedir, 'static', filepath)
    msg = "web service trying to serve: " + str(abspath)
    logger.info(msg)
    if os.path.isfile(abspath):
        filesize = os.path.getsize(abspath)
        req.sendFile(abspath, mimetype, force=1)
        d['timetable'].append(["reading file '%s'" % filepath, time.time() - atime])
        atime = time.time()
        d['status'] = 'ok'
        dataready = "%.3f" % (time.time() - starttime)
        d['dataready'] = dataready
        return 200, filesize, d  # ok
    else:
        d['status'] = 'fail'
        dataready = "%.3f" % (time.time() - starttime)
        d['dataready'] = dataready
        return 404, 0, d  # not found
