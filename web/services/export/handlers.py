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

import copy
import json
import logging
import os
import re
import time

from sqlalchemy.orm import undefer

from core.users import get_guest_user
from core import config
from core import Node, db
import core.users as users
from contenttypes import Collections, Home
from contenttypes import Data
from schema.schema import VIEW_DATA_ONLY, Metadatatype
from utils.date import format_date
from utils.pathutils import getBrowsingPathList, isDescendantOf
from utils.utils import esc, intersection, getMimeType, modify_tex
import web.services.jsonnode as jsonnode
from web.services.rssnode import template_rss_channel, template_rss_item, feed_channel_dict, try_node_date
from web.services.serviceutils import attribute_name_filter
from lxml import etree
from core.xmlnode import add_node_to_xmldoc, create_xml_nodelist


logg = logging.getLogger(__name__)
q = db.query


configured_host = config.get("host.name", "")

from web.services.cache import Cache
from web.services.cache import date2string as cache_date2string
import web.services.serviceutils as serviceutils

searchcache = Cache(maxcount=10, verbose=True)
resultcache = Cache(maxcount=25, verbose=True)

SEND_TIMETABLE = False


def add_mask_xml(xmlroot, node, mask_name, language):
    # mask handling
    if mask_name not in ["", "none"]:  # deliver every mask
        mask_obj = node.metadatatype.get_mask(mask_name)
        if mask_obj is not None:
            formated = mask_obj.getViewHTML([node], flags=8)
        else:
            mask = 'default'
            formated = node.show_node_text(labels=1, language=language)

    maskxml = etree.SubElement(xmlroot, "mask")
    maskxml.set("name", mask)
    maskxml.text = etree.CDATA(formated)


def _add_attrs_to_listinfo_item(xml_listinfo_item, attr_list, attribute_name_filter):
    for name, value in attr_list:
        if attribute_name_filter(name):
            xml_attribute = etree.SubElement(xml_listinfo_item, "attribute")
            xml_attribute.set("name", name)
            xml_attribute.text = etree.CDATA(unicode(value))


def _add_timetable_to_xmldoc(xmlroot, timetable):
    xml_tt = etree.SubElement(xmlroot, "service_handler_process_info")
    tt_sum = 0.0
    for i, x in enumerate(timetable):
        xml_step = etree.SubElement(xml_tt, "step")
        xml_step.set("order", "%02d" % i)
        xml_step.set("duration", "%.3f" % x[1])
        xml_step.set("unit", "sec.")
        xml_step.set("description", x[0])
        tt_sum += x[1]

    xml_allsteps = etree.SubElement(xml_tt, "allsteps")
    xml_allsteps.set("durationsum", "%.3f" % tt_sum)
    xml_allsteps.set("unit", "sec.")


def struct2xml(req, path, params, data, d, debug=False, singlenode=False, send_children=False, send_timetable=SEND_TIMETABLE):

    atime = time.time()

    # file types not to be included in listed node files
    exclude_filetypes = ['statistic']

    # sortfields
    sfields = d.setdefault('sfields', [])

    # mask
    mask = params.get('mask', 'default').lower()
    # we ignore the maskcache parameter

    xmlroot = etree.Element("response")
    xmlroot.set("status", d["status"])
    xmlroot.set("retrievaldate", d["retrievaldate"])
    xmlroot.set("servicereactivity", d["dataready"])
    xmlroot.set("oauthuser", d.get("oauthuser", ""))
    xmlroot.set("username", d.get("username", ""))
    xmlroot.set("userid", d.get("userid", ""))

    language = params.get('lang', '')

    if d['status'] == 'ok':
        if singlenode:
            n = d['nodelist'][0]
            if not send_children:
                add_node_to_xmldoc(n, xmlroot, exclude_filetypes=exclude_filetypes, attribute_name_filter=attribute_name_filter)
            else:
                xml_nodelist = create_xml_nodelist(xmlroot)
                add_node_to_xmldoc(n, xml_nodelist, children=True, exclude_filetypes=exclude_filetypes,
                                           attribute_name_filter=attribute_name_filter)

            add_mask_xml(xmlroot, n, mask, language)

        else:
            xml_nodelist = create_xml_nodelist()
            xml_nodelist.set("start", d["nodelist_start"])
            xml_nodelist.set("count", d["nodelist_limit"])
            xml_nodelist.set("countall", d["nodelist_countall"])

            for n in d['nodelist']:
                add_node_to_xmldoc(n, xmlroot, exclude_filetypes=exclude_filetypes, attribute_name_filter=attribute_name_filter)
                add_mask_xml(xmlroot, n, mask, language)

        # append a shortlist with id, name and type of the nodes
        # from result_shortlist = [[i, x.id, x.name, x.type, attr_list(x, sfields)] for i, x in enumerate(nodelist)]

        xml_listinfo = etree.SubElement(xmlroot, "listinfo")
        xml_listinfo.set("sortfield", d["sortfield"])
        xml_listinfo.set("sortdirection", d["sortdirection"])

        for p in d['result_shortlist']:
            xml_item = etree.SubElement(xml_listinfo, "item")
            xml_item.set("index", p[0])
            xml_item.set("id", p[1])
            xml_item.set("type", p[3])

            if sfields:
                _add_attrs_to_listinfo_item(xml_item, p[4], attribute_name_filter)

        if send_timetable:
            # append info on how long the steps took to get the result
            timetable = d['timetable'][:]
            timetable.append(['build result xml', time.time() - atime])
            _add_timetable_to_xmldoc(xmlroot, timetable)

    else:
        xml_errormessage = etree.SubElement(xmlroot, "errormessage")
        xml_errormessage.text = etree.CDATA(d["errormessage"])

    return etree.tostring(xmlroot, pretty_print=True, encoding="utf8")


def struct2template_test(req, path, params, data, d, debug=False, singlenode=False, send_children=False, send_timetable=SEND_TIMETABLE):
    nodelist = d['nodelist']

    if 'add_shortlist' not in req.params:
        d['result_shortlist'] = []

    d['nodelist'] = [jsonnode.buildNodeDescriptor(req, n, children=send_children) for n in nodelist]
    json_timetable = d['timetable'][:]

    template = req.params.get("template", u"record $$[_rcd]$$: id=$$[id]$$: no-template-given\n")
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
                x = x.replace((u"$$[%s]$$" % attr), nd[0].get(attr, ''))
            elif attr.startswith("_rc"):
                x = x.replace((u"$$[%s]$$" % attr), attr.replace("_rc", "%") % rc)
            elif attr == "id":
                x = x.replace(u"$$[id]$$", unicode(nd[0].get("id")))
            elif attr in ["nodename", "nodetype"]:
                x = x.replace((u"$$[%s]$$" % attr), nd[0].get(attr.replace("node", ""), ''))
            else:
                x = x.replace((u"$$[%s]$$" % attr), nd[0]["attributes"].get(attr, ''))
        res = res + x

    d['timetable'] = []
    if send_timetable:
        d['timetable'] = json_timetable

    d['timetable'] = json_timetable
    d['dataready'] = ("%.3f" % (time.time() - d['build_response_start']))

    res = res.replace("\\n", "\n").replace("\\l", "\l").replace("\\r", "\r").replace("\\t", "\t")

    if 'bom' in params.keys():
        return res.encode("utf_8_sig") # this codec adds BOM
    else:
        return res.encode("utf8")


def struct2json(req, path, params, data, d, debug=False, singlenode=False, send_children=False, send_timetable=SEND_TIMETABLE):
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


def struct2csv(req, path, params, data, d, debug=False, sep=u';', string_delimiter=u'"', singlenode=False, send_children=False):


    # delimiter and separator can be transferred by the query
    # this dictionary decodes the characters that would disturb in the url
    trans = {
        'none': u'',
        'tab': u'\t',
        'quote': u"'",
        'dquote': u'"',
    }

    string_delimiter = params.get('delimiter', string_delimiter)
    if string_delimiter.lower() in trans.keys():
        string_delimiter = trans[string_delimiter.lower()]

    sep = params.get('sep', sep)
    if sep.lower() in trans.keys():
        sep = trans[sep.lower()]

    def join_row(row):
        row = [unicode(x) for x in row]

        try:
            if string_delimiter:
                res = string_delimiter + \
                    ((string_delimiter + sep +
                      string_delimiter).join([x.replace(string_delimiter, u"'") for x in row])) + string_delimiter
            else:
                res = sep.join(row)
        except:
            res = u""
            for x in row:
                if string_delimiter:
                    x = x.replace(string_delimiter, u"'")
                res += string_delimiter + x + string_delimiter + sep

            if res:
                res = res[0:-len(sep)]
        return res

    r = u''

    if d['status'].lower() == 'fail':
        header = ['status', 'html_response_code', 'errormessage', 'retrievaldate', 'dataready']
        r = join_row(header) + u'\r\n'
        r += join_row(map(lambda x: d[x], header))
        return r

    rd = {}
    keys = set()
    csv_nodelist = d['nodelist'][:]
    csvattrs = []
    if 'csvattrs' in params:
        csvattrs = [attr.strip() for attr in params['csvattrs'].split(',')]

    for i, n in enumerate(csv_nodelist):
        rd[i] = {}
        rd[i]['id'] = unicode(n.id)
        rd[i]['name'] = n.name
        rd[i]['type'] = n.type + "/" + n.schema
        attrs = copy.deepcopy(n.attributes)
        rd[i]['attributes'] = attrs
        keys = keys.union(attrs.keys())

    if csvattrs:
        keys = set(csvattrs)

    sorted_tuples = sorted([(x.lower(), x) for x in list(keys)])
    attr_header = [x[1] for x in sorted_tuples]

    # sortfields shall appear early (after id, type and name of the node) of the csv table
    if 'sfields' in d.keys() and d['sfields']:
        for sfield in d['sfields']:
            if sfield in attr_header:
                attr_header.remove(sfield)
        attr_header = d['sfields'] + attr_header

    # filter attribute names
    attr_header = filter(attribute_name_filter, attr_header)

    header = [u'count', u'id', u'type', u'name'] + attr_header
    r = join_row(header) + u'\r\n'

    for i, n in enumerate(csv_nodelist):
        row = [unicode(i), rd[i]['id'], rd[i]['type'], rd[i]['name']]
        for attr in attr_header:
            # handle sortfields in attr_header that are not attributes
            if attr in ['node.id', 'node.name', 'node.type']:
                continue
            elif attr in ['node.orderpos']:
                row.append(q(Node).get(rd[i]['id']).get(attr))
            else:
                row.append(rd[i]['attributes'].setdefault(attr, u''))
        r += join_row(row) + u'\r\n'

    if 'bom' in params.keys():
        return r.encode("utf_8_sig") # this codec adds BOM
    else:
        return r.encode("utf8")


def struct2rss(req, path, params, data, struct, debug=False, singlenode=False, send_children=False):
    nodelist = struct['nodelist']
    language = params.get('lang', 'en')
    items_list = []

    host = u"http://" + unicode(req.get_header("HOST") or configured_host)
    collections = q(Collections).one()
    user = get_guest_user()

    for n in nodelist:
        nodename = n.name
        nodeid = str(n.id)
        updatetime = utime = try_node_date(n)

        # categories to be included in all items - mask generated or not
        default_categories = u'<category>node type: ' + n.type + '/' + n.schema + u'</category>\r\n'

        # check for export mask for this node
        try:
            try:
                mdt = n.metadatatype
            except:
                mdt = None
            mask = mdt.getMask('rss')
            if mask.get('masktype') != 'export':
                mask = None
        except:
            mask = None

        if mask:
            item_xml = u'<item>\r\n' + mask.getViewHTML([n], flags=8) + default_categories + u'\r\n</item>\r\n'
            items_list = items_list + [(updatetime, nodename, nodeid, item_xml)]
            continue

        # no rss export mask: build default item from nodesmall mask
        item_d = {}

        browsingPathList = getBrowsingPathList(n)
        browsingPathList = [x for x in browsingPathList if x[-1].has_read_access(user=user) and x[-1].is_descendant_of(collections)]
        browsingPathList_names = [map(lambda x: x.name, browsingPath) for browsingPath in browsingPathList]

        # assumption: longest path is most detailled and illustrative for being used in the title
        x = sorted([[len(p), i, p] for i, p in enumerate(browsingPathList_names)])
        x.reverse()
        try:
            most_detailed_path = x[0][2]
        except:  # browsing path list may be empty (for directories, collections, ...)
            most_detailed_path = ''

        item_d['title'] = esc(u"{} ({}, {}/{}) {}".format(nodename or u'-unnamed-node-',
                                                          nodeid, n.type, n.schema, u"/".join(most_detailed_path)))
        item_d['item_pubDate'] = utime
        item_d['guid'] = host + u'/node?id=%s' % nodeid
        item_d['link'] = host + u'/node?id=%s' % nodeid

        if mdt:
            lang_mask = mdt.masks.filter(Node.name.startswith(u"nodesmall")).filter(Node.a.language == language).first()
            if lang_mask is not None:
                mask = lang_mask
            else:
                mask = mdt.get_mask('nodesmall')
        else:
            mask = None

        if mask is not None:
            attr_list = mask.getViewHTML([n], VIEW_DATA_ONLY, language)  # [[attr_name, value, label, type], ...]
        else:
            attr_list = [['', n.id, 'node id', ''], ['', n.name, 'node name', ''], ['', n.type + "/" + n.schema, 'node type', ''], ]

        description = u''
        for x in attr_list:
            description = description + (u'''<b>%s: </b>%s<br/>\r\n''' % (x[2], x[1]))

        item_d['description'] = description
        categories = default_categories

        for x in browsingPathList_names:
            categories = categories + u'<category>' + esc(u'/'.join(x)) + u'</category>\r\n'

        ddcs = n.get('ddc').strip()
        if ddcs.strip():
            ddcs = ddcs.split(';')
            for ddc in ddcs:
                categories = categories + u'<category>' + esc(ddc) + u'</category>\r\n'

        subjects = n.get('subject').strip()
        if subjects:
            subjects = subjects.split(';')
            for subject in subjects:
                categories = categories + u'<category>' + esc(subject) + u'</category>\r\n'

        item_d['categories'] = categories

        for k, v in item_d.items():
            item_d[k] = v

        items_list = items_list + [(updatetime, nodename, nodeid, (template_rss_item % item_d))]

    if items_list:
        items_list.sort()
        items_list.reverse()

    items = ''
    for x in items_list:
        items += (x[3] + u'\r\n')

    pubDate = lastBuildDate = format_date(format='rfc822')

    struct['dataready'] = (u"%.3f" % (time.time() - struct['build_response_start']))

    fcd = feed_channel_dict.copy()
    fcd['lang'] = u'de'
    fcd['pubdate'] = pubDate
    fcd['lastbuild'] = lastBuildDate
    fcd['link'] = host
    fcd['atom_link'] = host + req.fullpath
    fcd['image_title'] = 'testlogo'
    fcd['image_link'] = host + u'/img/testlogo.png'
    fcd['image_url'] = host + u'/img/testlogo.png'

    if 'feed_info' in params:
        for k, v in params['feed_info'].items():
            fcd[k] = v
    else:
        fcd['title'] = host + req.fullpath + req.query
    fcd['items'] = items
    s = template_rss_channel % fcd  # params['feed_info']

    return s.encode("utf8")

supported_formats = [
    [['xml', ''], struct2xml, 'text/xml'],
    [['json'], struct2json, 'application/json'],
    [['csv'], struct2csv, 'text/csv'],
    [['template_test'], struct2template_test, 'text/plain'],
    [['rss'], struct2rss, 'application/rss+xml'],
]


def get_node_children_struct(
        req, path, params, data, id, debug=True, allchildren=False, singlenode=False, parents=False, send_children=False):
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

        # users.getUser(_username) returned user
        timetable.append(['''oauth: users.getUser(%r) returned %r (%r, %r, %r) -> groups: %r''' %
                          (_username, _user, _user.getName(), _user.getUserID(), _user.getUserType(), _user.getGroups()), time.time() -
                          atime])
        atime = time.time()

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
        user = get_guest_user()

    if user is not None:
        res['username'] = user.login_name
        res['userid'] = user.id
    result_shortlist = []

    nodelist = []
    res['nodelist'] = nodelist

    # query parameters
    nodelist_type = params.get('type', '')  # return only nodes of given type like dissertation/diss
    parent_type = params.get('parent_type', '')  # return only nodes that have only parents of  given type like folder or collection
    send_versions = params.get('send_versions', '').lower()  # return also nodes that are older versions of other nodes
    # return only nodes that have an EXIF location that lies between the given lon,lat values
    exif_location_rect = params.get('exif_location_rect', '')
    mdt_name = params.get('mdt_name', '')
    attrreg = params.get('attrreg', '')
    node_query = params.get('node_query', '')  # node query
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
        node = q(Node).get(id)
    except:
        logg.exception("exception in get_node_children_struct, return 404")
        res['status'] = 'fail'
        res['html_response_code'] = '404'  # not found
        res['errormessage'] = 'node not found'
        res['build_response_end'] = time.time()
        dataready = "%.3f" % (res['build_response_end'] - starttime)
        res['dataready'] = dataready
        return res

    home = q(Home).one()
    collections = q(Collections).one()
    # check node access
    if user is not None and node.has_read_access(user=user) and (node.is_descendant_of(collections) or node.is_descendant_of(home)):
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
    if node_query:
        cache_key = (path).split('?')[0] + '|node_query=' + node_query  # req.path
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
            searchresult = node.search(node_query)
            timetable.append(['execute search node_query=%s on node (%s, %s, %s) resulting in %d nodes' %
                              (node_query, node.id, node.type, node.name, len(searchresult)), time.time() - atime])
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
    if mdt_name:
        mdt = q(Metadatatype).filter_by(name=mdt_name).scalar()
        if not mdt:
            res['status'] = 'fail'
            res['html_response_code'] = '404'  # not found
            res['errormessage'] = 'no such metadata type: ' + mdt_name
            res['build_response_end'] = time.time()
            dataready = "%.3f" % (res['build_response_end'] - starttime)
            res['dataready'] = dataready
            return res
        typed_node_id_list = db.get_nids_by_type_suffix(mdt_name)
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
                          (node.id, node.name, node.type, len(nodelist)), time.time() - atime])
        atime = time.time()
    elif allchildren:
        if node_query and not mdt_name:
            nodelist = searchresult
        elif mdt_name and not node_query:
            if typed_nodelist:
                nodelist = tree.NodeList([x for x in typed_nodelist if (guestAccess.hasAccess(x, 'read') and (isDescendantOf(x, node)))])
                timetable.append(['''access filter of typed (%s) nodes -> (%d nodes)''' % (mdt_name, len(nodelist)), time.time() - atime])
                atime = time.time()
        elif mdt_name and node_query:
            filtered_nodelist = tree.NodeList(
                [x for x in typed_nodelist if (guestAccess.hasAccess(x, 'read') and (isDescendantOf(x, node)))])
            timetable.append(['''access filter of typed (%s) nodes -> (%d nodes)''' % (mdt_name, len(nodelist)), time.time() - atime])
            atime = time.time()
            nodelist = intersection([filtered_nodelist, searchresult])
            timetable.append(['''intersection of typed (%s) nodes with searchresult -> (%d nodes)''' %
                              (mdt_name, len(nodelist)), time.time() - atime])
            atime = time.time()
        else:
            # refuse request for all children on collections root
            if node.id != q(Collections.id).scalar():
                nodelist = [node] + node.all_children_by_query(q(Data)).options(undefer(Node.attrs)).all()
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
                              (node.id, node.name, node.type, len(nodelist)), time.time() - atime])
            atime = time.time()
    else:
        nodelist = node.getChildren()
        timetable.append(['''get direct children for node %s, '%s', '%s' -> (%d nodes)''' %
                          (node.id, node.name, node.type, len(nodelist)), time.time() - atime])
        atime = time.time()
        if node_query:
            nodelist = intersection([searchresult, nodelist])
            timetable.append(['''searchresult filter with direct children for node %s, '%s', '%s' -> (%d nodes)''' %
                              (node.id, node.name, node.type, len(nodelist)), time.time() - atime])
            atime = time.time()
        if mdt_name:
            nodelist = intersection([typed_nodelist, nodelist])
            timetable.append(['''filter typed nodes with direct children for node %s, '%s', '%s' -> (%d nodes)''' %
                              (node.id, node.name, node.type, len(nodelist)), time.time() - atime])
            atime = time.time()

    timetable.append(['get set of ids of nodelist', time.time() - atime])
    atime = time.time()

    if not mdt_name and not node_query:
        # XXX: we don't check here if permissions have changed
        nodelist = [x for x in nodelist if (x.has_read_access(user=user))]
        timetable.append(['filter access with hasAccess (%d nodes -> %d nodes)' %
                          (len(nodelist), len(nodelist)), time.time() - atime])
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

        nodetuples = [map(lambda sfield: x.get_special(sfield), sfields) + [x.id, x] for x in nodelist]

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
                result_from_cache = params['jsoncallback'] + result_from_cache[result_from_cache.find("({"):]

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

        for supported_format in supported_formats:
            if res_format in supported_format[0]:
                atime = time.time()
                formatIsSupported = True
                s = supported_format[1](req, path, params, data, d, debug=debug, singlenode=singlenode, send_children=send_children)
                if res_format == 'json' and 'jsoncallback' in params:
                    s = params['jsoncallback'] + '(' + s + ')'
                # XXX: clients can override the content_type by setting the mimetype param
                # XXX: this is ugly, but we keep it for compatibility
                mimetype = params.get('mimetype', supported_format[2])

                # append correct charset if client didn't force another value
                # it doesn't make sense to set it in the client to a different charset than utf8, but it was possible in the past...
                if "charset=" in mimetype:
                    content_type = mimetype
                else:
                    content_type = mimetype + "; charset=utf-8"

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
            content_type = "text/xml; charset=utf-8"

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

        s = modify_tex(s.decode("utf8"), 'strip').encode("utf8")

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

    # (format) Expires: Mon, 28 Nov 2011 12:41:22 GMT
    # see core.athana.build_http_date
    # req.reply_headers['Expires'] = time.strftime ('%a, %d %b %Y %H:%M:%S GMT', time.gmtime(time.time()+60.0)) # 1 minute

    # remark: on 2011-12-01 switched response from req.write to req.sendAsBuffer for performance reasons
    # (before: ) req.write(s)
    req.sendAsBuffer(s, content_type, force=1)
    d['timetable'].append(["executed req.sendAsBuffer, %d bytes, content type='%s'" % (len(s), content_type), time.time() - atime])
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
    from contenttypes.data import get_maskcache_report
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
    logg.info("web service trying to serve: ", abspath)
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
