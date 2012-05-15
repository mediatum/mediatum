"""
 mediatum - a multimedia content repository

 Copyright (C) 2007 Arne Seifert <seiferta@in.tum.de>
 Copyright (C) 2007 Matthias Kramm <kramm@in.tum.de>

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
import sys
import logging
import time

import core.tree as tree
import core.athana as athana
import core.config as config
import core.users as users
from schema.schema import loadTypesFromDB, getMetaFieldTypeNames, getMetaFieldTypes, getMetadataType, VIEW_DATA_ONLY, VIEW_SUB_ELEMENT, VIEW_HIDE_EMPTY, VIEW_DATA_EXPORT, dateoption
from core.translation import lang
from utils.utils import Menu, esc
from export.exportutils import runTALSnippet, default_context
from web.services.cache import date2string as cache_date2string

languages = [lang.strip() for lang in config.get("i18n.languages").split(",") if lang.strip()]

# for TAL templates from mask cache
context = default_context.copy()
context['host'] = "http://" + config.get("host.name")

DEFAULT_MASKCACHE = 'deep'  # 'deep' | 'shallow' | None

# for deep mask caching
maskcache = {}
maskcache_accesscount = {}
maskcache_msg = '| cache initialized %s\r\n|\r\n' % cache_date2string(time.time(), '%04d-%02d-%02d-%02d-%02d-%02d')

# for shallow mask caching
maskcache_shallow = {}


def get_maskcache_report():
    s = maskcache_msg + "| %d lookup keys in cache, total access count: %d\r\n|\r\n"
    total_access_count = 0
    for k, v in sorted(maskcache_accesscount.items()):
        s += "| %s : %s\r\n" % (k.ljust(60, '.'), str(v).rjust(8, '.'))
        total_access_count += v
    return s % (len(maskcache_accesscount), total_access_count)


def flush_maskcache(req=None):
    global maskcache, maskcache_accesscount, maskcache_shallow, maskcache_msg
    logging.getLogger("everything").info("going to flush maskcache, content is: \r\n" + get_maskcache_report())
    maskcache = {}
    maskcache_accesscount = {}
    maskcache_shallow = {}
    if req:
        user = users.getUserFromRequest(req)
        logging.getLogger("everything").info("flush of masks cache triggered by user %s with request on '%s'" % (user.name, req.path))

        sys.stdout.flush()
    maskcache_msg = '| cache last flushed %s\r\n|\r\n' % cache_date2string(time.time(), '%04d-%02d-%02d-%02d-%02d-%02d')


def make_lookup_key(node, language=languages[0], labels=True):
    global languages
    flaglabels = 'nolabels'
    if labels:
        flaglabels = 'uselabels'

    if language in languages:
        return "%s_%s_%s" % (str(node.type), str(language), flaglabels)
    else:
        return "%s_%s_%s" % (str(node.type), languages[0], flaglabels)


def get_maskcache_entry(lookup_key):
    try:
        res = maskcache[lookup_key]
        maskcache_accesscount[lookup_key] = maskcache_accesscount[lookup_key] + 1
    except:
        res = None
    return res


class Default(tree.Node):
    def getTypeAlias(node):
        return "default"

    def getCategoryName(node):
        return "undefined"

    def show_node_big(node, req, template="", macro=""):
        return "Unknown datatype: "+node.type

    def show_node_image(node, language=None):
        return athana.getTAL("contenttypes/default.html", {'children':node.getChildren().sort(), 'node':node}, macro="show_node_image")

    def show_node_text(node, words=None, language=None, separator="", labels=0, cachetype=DEFAULT_MASKCACHE):
        if cachetype not in ['shallow', 'deep']:
            return node.show_node_text_orignal(words=words, language=language, separator=separator, labels=labels)
        elif cachetype == 'deep':
            return node.show_node_text_deep(words=words, language=language, separator=separator, labels=labels)
        else:
            return node.show_node_text_shallow(words=words, language=language, separator=separator, labels=labels)

    """ format preview node text """
    # original
    def show_node_text_orignal(node, words=None, language=None, separator="", labels=0):
        if separator == "":
            separator = "<br/>"
        metatext = list()
        mask = node.getMask("nodesmall")
        for m in node.getMasks("shortview", language=language):
            mask = m

        if mask:
            fields = mask.getMaskFields()
            for field in mask.getViewHTML([node], VIEW_DATA_ONLY, language=language, mask=mask):
                if len(field) >= 2:
                    value = field[1]
                else:
                    value = ""

                if words != None:
                    value = highlight(value, words, '<font class="hilite">', "</font>")

                if value:
                    if labels:
                        for f in fields:
                            if f.getField().getName() == field[0]:
                                metatext.append("<b>" + f.getLabel() + ":</b> " + value)
                                break
                    else:
                        if field[0].startswith("author"):
                            value = '<span class="author">' + value + '</span>'
                        if field[0].startswith("subject"):
                            value = '<b>' + value + '</b>'
                        metatext.append(value)
        else:
            metatext.append('&lt;smallview mask not defined&gt;')

        return separator.join(metatext)

    # deep caching
    def show_node_text_deep(node, words=None, language=None, separator="", labels=0):

        def render_mask_template(node, mfs, words=None, separator="", skip_empty_fields=True):
            '''
               mfs: [mask] + list_of_maskfields
            '''
            res = []
            exception_count = {}
            mask = mfs[0]
            for node_attribute, fd in mfs[1:]:
                metafield_type = fd['metafield_type']
                if metafield_type in ['date', 'url']:
                    exception_count[metafield_type] = exception_count.setdefault(metafield_type, 0) + 1
                    value = node.get(node_attribute)
                    value_a = value
                    try:
                        value = fd['metadatatype'].getFormatedValue(fd['element'], node, language=language, mask=mask)[1]
                    except:
                        value = fd['metadatatype'].getFormatedValue(fd['element'], node, language=language)[1]
                else:
                    value = node.get(node_attribute)
                    if value.find('&lt;') >= 0:
                        # replace variables
                        for var in re.findall(r'&lt;(.+?)&gt;', value):
                            if var == "att:id":
                                value = value.replace("&lt;" + var + "&gt;", node.id)
                            elif var.startswith("att:"):
                                val = node.get(var[4:])
                                if val == "":
                                    val = "____"

                                value = value.replace("&lt;" + var + "&gt;", val)
                        value = value.replace("&lt;", "<").replace("&gt;", ">")

                    if value.find('<') >= 0:
                        # replace variables
                        for var in re.findall(r'\<(.+?)\>', value):
                            if var == "att:id":
                                value = value.replace("<" + var + ">", node.id)
                            elif var.startswith("att:"):
                                val = node.get(var[4:])
                                if val == "":
                                    val = "____"

                                value = value.replace("&lt;" + var + "&gt;", val)
                        value = value.replace("&lt;", "<").replace("&gt;", ">")

                    if value.find('tal:') >= 0:
                        context['node'] = node
                        value = runTALSnippet(value, context)

                    # don't escape before running TAL
                    if (not value) and fd['default']:
                        default = fd['default']
                        if fd['default_has_tal']:
                            context['node'] = node
                            value = runTALSnippet(default, context)
                        else:
                            value = default

                if skip_empty_fields and not value:
                    continue

                if fd["unit"]:
                    value = value + " " + fd["unit"]
                if fd["format"]:
                    value = fd["format"].replace("<value>", value)
                if words:
                    value = highlight(value, words, '<font class="hilite">', "</font>")
                res.append(fd["template"] % value)
            if exception_count and len(exception_count.keys()) > 1:
                pass
            return separator.join(res)

        if not separator:
            separator = "<br/>"

        lookup_key = make_lookup_key(node, language, labels)

        if lookup_key in maskcache:
            mfs = maskcache[lookup_key]
            res = render_mask_template(node, mfs, words=words, separator=separator)
            maskcache_accesscount[lookup_key] = maskcache_accesscount[lookup_key] + 1
            return res
        else:
            metatext = list()
            mask = node.getMask("nodesmall")
            for m in node.getMasks("shortview", language=language):
                mask = m

            if mask:
                mfs = [mask]  # mask fields
                values = []
                fields = mask.getMaskFields()
                ordered_fields = [(f.orderpos, f) for f in fields]
                ordered_fields.sort()
                for orderpos, field in ordered_fields:
                    fd = {}  # field descriptor

                    element = field.getField()
                    t = getMetadataType(element.get("type"))

                    fd['format'] = field.getFormat()
                    fd['unit'] = field.getUnit()
                    label = field.getLabel()
                    fd['label'] = label
                    #fd['separator'] = field.getSeparator()
                    default = field.getDefault()
                    fd['default'] = default
                    fd['default_has_tal'] = (default.find('tal:') >= 0)

                    fd['metadatatype'] = t
                    fd['metafield_type'] = field.getChildren()[0].get('type')
                    fd['element'] = element

                    def getNodeAttributeName(field):
                        metafields = [x for x in field.getChildren() if x.type == 'metafield']
                        if len(metafields) != 1:
                            logging.getLogger("error").error("maskfield %s zero or multiple metafield child(s)" % field.id)
                        return metafields[0].name

                    node_attribute = getNodeAttributeName(field)
                    fd['node_attribute'] = node_attribute

                    def build_field_template(field_descriptor):
                        if labels:
                            template = "<b>" + field_descriptor['label'] + ":</b> %s"
                        else:
                            if field_descriptor['node_attribute'].startswith("author"):
                                template = '<span class="author">%s</span>'
                            elif field_descriptor['node_attribute'].startswith("subject"):
                                template = '<b>%s</b>'
                            else:
                                template = "%s"
                        return template

                    template = build_field_template(fd)

                    fd['template'] = template
                    long_field_descriptor = [node_attribute, fd]
                    mfs = mfs + [long_field_descriptor]

                maskcache[lookup_key] = mfs
                maskcache_accesscount[lookup_key] = 0
                res = render_mask_template(node, mfs, words=words, separator=separator)
                return res

            else:
                return '&lt;smallview mask not defined&gt;'

            if words != None:
                value = highlight(value, words, '<font class="hilite">', "</font>")

            return separator.join(metatext)

    # shallow caching
    def show_node_text_shallow(node, words=None, language=None, separator="", labels=0):
        global maskcache_shallow

        def render_mask_template(node, mfs, words=None, separator=""):
            mask, fields, labels_data = mfs
            metatext = list()

            for field in mask.getViewHTML([node], VIEW_DATA_ONLY, language=language, mask=mask):
                if len(field) >= 2:
                    value = field[1]
                else:
                    value = ""

                if words != None:
                    value = highlight(value, words, '<font class="hilite">', "</font>")

                if value:
                    if labels:
                        for f, f_name, f_label in labels_data:
                            if f_name == field[0]:
                                metatext.append("<b>" + f_label + ":</b> " + value)
                                break
                    else:

                        if field[0].startswith("author"):
                            value = '<span class="author">' + value + '</span>'
                        if field[0].startswith("subject"):
                            value = '<b>' + value + '</b>'
                        metatext.append(value)

            return separator.join(metatext)

        if not separator:
            separator = "<br/>"

        lookup_key = make_lookup_key(node, language, labels)

        if lookup_key in maskcache_shallow:
            mfs = maskcache_shallow[lookup_key]
            res = render_mask_template(node, mfs, words=words, separator=separator)
            return res
        else:
            # this list will be cached
            to_be_cached = []

            metatext = list()
            mask = node.getMask("nodesmall")
            for m in node.getMasks("shortview", language=language):
                mask = m

            if mask:
                fields = mask.getMaskFields()

                #####
                def getNodeAttributeName(field):
                    metafields = [x for x in field.getChildren() if x.type == 'metafield']
                    if len(metafields) != 1:
                        logging.getLogger("error").error("maskfield %s zero or multiple metafield child(s)" % field.id)
                    return metafields[0].name
                #####

                if labels:
                    labels_data = [(f, f.getField().getName(), f.getLabel()) for f in fields]
                else:
                    pass
                    labels_data = []

                for field in mask.getViewHTML([node], VIEW_DATA_ONLY, language=language, mask=mask):
                    if len(field) >= 2:
                        value = field[1]
                    else:
                        value = ""

                    if words != None:
                        value = highlight(value, words, '<font class="hilite">', "</font>")

                    if value:
                        if labels:
                            for f, f_name, f_label in labels_data:
                                if f_name == field[0]:
                                    metatext.append("<b>" + f_label + ":</b> " + value)
                                    break
                        else:

                            if field[0].startswith("author"):
                                value = '<span class="author">' + value + '</span>'
                            if field[0].startswith("subject"):
                                value = '<b>' + value + '</b>'
                            metatext.append(value)

                to_be_cached = [mask, fields, labels_data]
                maskcache_shallow[lookup_key] = to_be_cached

            else:
                metatext.append('&lt;smallview mask not defined&gt;')
            return separator.join(metatext)

    def isContainer(node):
        return 0

    def getTreeIcon(node):
        return ""

    def isSystemType(node):
        return 0

    def get_name(node):
        return node.name

    def getTechnAttributes(node):
        return {}

    def has_object(node):
        return True

    def getFullView(node, language):
        masks = node.getMasks(type="fullview", language=language)
        if len(masks) > 1:
            for m in masks:
                if m.getLanguage() == language:
                    return m
            #if not mask:
            for m in masks:
                if m.getLanguage() in ["", "no"]:
                    return m
        elif len(masks) == 0:
            return tree.Node("", type="mask")
        else:
            return masks[0]

    def getSysFiles(node):
        return []

    def buildLZAVersion(node):
        print "no lza builder implemented"

    def getEditMenuTabs(node):
        menu = list()
        try:
            submenu = Menu("menuglobals", "..")
            menu.append(submenu)

        except TypeError:
            pass
        return  ";".join([m.getString() for m in menu])

    def getDefaultEditTab(node):
        return "view"
