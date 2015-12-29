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
from warnings import warn

from mediatumtal import tal
import core.acl as acl
from core import Node
import core.config as config
from core.translation import lang
from core.styles import getContentStyles
from core.transition.postgres import check_type_arg_with_schema
from schema.schema import getMetadataType, VIEW_DATA_ONLY, VIEW_HIDE_EMPTY, SchemaMixin
from utils.utils import Menu, highlight, format_filesize
from export.exportutils import runTALSnippet, default_context
from web.services.cache import date2string as cache_date2string
from core.database.postgres.node import children_rel
from mock import MagicMock
from sqlalchemy.orm import object_session

logg = logging.getLogger(__name__)

# for TAL templates from mask cache
context = default_context.copy()
### XXX: does this work without hostname? Can we remove this?
context['host'] = "http://" + config.get("host.name", "")


def init_maskcache():
    global maskcache, maskcache_accesscount, maskcache_msg
    maskcache = {}
    maskcache_accesscount = {}
    maskcache_msg = '| cache initialized %s\r\n|\r\n' % cache_date2string(time.time(), '%04d-%02d-%02d-%02d-%02d-%02d')


def get_maskcache_report():
    s = maskcache_msg + "| %d lookup keys in cache, total access count: %d\r\n|\r\n"
    total_access_count = 0
    for k, v in sorted(maskcache_accesscount.items()):
        s += u"| {} : {}\r\n".format(k.ljust(60, '.'),
                                     unicode(v).rjust(8, '.'))
        total_access_count += v
    return s % (len(maskcache_accesscount), total_access_count)


def flush_maskcache(req=None):
    from core import users
    global maskcache, maskcache_accesscount, maskcache_msg
    logg.info("going to flush maskcache, content is: \r\n%s", get_maskcache_report())
    maskcache = {}
    maskcache_accesscount = {}
    if req:
        user = users.getUserFromRequest(req)
        logg.info("flush of masks cache triggered by user %s with request on '%s'", user.login_name, req.path)

        sys.stdout.flush()
    maskcache_msg = '| cache last flushed %s\r\n|\r\n' % cache_date2string(time.time(), '%04d-%02d-%02d-%02d-%02d-%02d')


def make_lookup_key(node, language=None, labels=True):
    languages = config.languages
    if language is None:
        language = languages[0]
    flaglabels = 'nolabels'
    if labels:
        flaglabels = 'uselabels'

    if language in languages:
        return "%s/%s_%s_%s" % (node.type, node.schema, language, flaglabels)
    else:
        return "%s/%s_%s_%s" % (node.type, node.schema, languages[0], flaglabels)


def get_maskcache_entry(lookup_key):
    try:
        res = maskcache[lookup_key]
        maskcache_accesscount[lookup_key] += 1
    except:
        res = None
    return res


class Data(Node):

    """Abstract base class for all node classes which can be viewed / fetched by frontend / api users.
    Methods in this class are concerned with viewing / representing the contents of the data node.

    In other words: Node classes which don't inherit from this class are seen as internal 'system types'.
    """

    content_children = children_rel("Content")

    @classmethod
    def get_all_datatypes(cls):
        """Returns all known subclasses of cls except `Collections` and `Home`"""
        return cls.get_all_subclasses(filter_classnames=("collections", "home"))

    @classmethod
    def getTypeAlias(cls):
        return "default"

    @classmethod
    def getOriginalTypeName(cls):
        return "original"

    @classmethod
    def getCategoryName(cls):
        return "undefined"

    def getDetailsCondition(self):
        '''checks if 'details' should be displayed
           or not

           :return: boolean
        '''
        if self.children.count() > 0:
            return True
        else:
            return len(self.children.all()) > 0 in self.children.all()

    def getFurtherDetailsCondition(self, req):
        '''checks if 'further details'
           should be displayed or not

           :return: boolean
        '''
        s = object_session(self)
        q = s.query

        if q(Node).get((req.params.get('pid', self.id))).children.count() == 1:
            return False
        if self.parents.first() is not None:
            return True
        else:
            return len(self.children.all()) > 0 in self.children.all()

    def getParentInformation(self, req):
        '''sets diffrent used Information
           to a dict object

           :param req: request object
           :return: dict parentInformation
        '''
        s = object_session(self)
        q = s.query

        parentInformation = {}
        pid = req.params.get('pid', self.id)
        parentInformation['parent_node_id'] = pid
        from contenttypes.container import Container

        if self.children.count() > 0 and not isinstance(self, Container):
            parentInformation['children_list'] = self.children.all()
        else:
            parentInformation['children_list'] = []
        if len([sib.id for sib in self.parents.filter_by(id=req.params.get('pid', self.id)).all()]) != 0:
            parentInformation['parent_condition'] = True
            parentInformation['siblings_list'] = q(Node).get(pid).children.filter(Node.id is not self.id).all()
        else:
            parentInformation['parent_condition'] = False
            if len([p for p in self.parents]) > 0:
                parentInformation['siblings_list'] = self.parents.first().children.all()
            else:
                parentInformation['siblings_list'] = []

        parentInformation['display_siblings'] = pid != self.id
        parentInformation['parent_is_container'] = self.parents.filter(isinstance(self, Container)).all()
        parentInformation['details_condition'] = self.getDetailsCondition()
        parentInformation['further_details'] = self.getFurtherDetailsCondition(req)

        return parentInformation

    def show_node_big(self, req, template="", macro=""):
        mask = self.getFullView(lang(req))

        if template == "":
            styles = getContentStyles("bigview", contenttype=self.getContentType())
            if len(styles) >= 1:
                template = styles[0].getTemplate()
        # hide empty elements}, macro)

        return req.getTAL(template,
                          {'node': self,
                           'metadata': mask.getViewHTML([self], VIEW_HIDE_EMPTY),
                           'format_size': format_filesize,
                           'parentInformation': self.getParentInformation(req)
                          })

    def show_node_image(self, language=None):
        return tal.getTAL(
            "contenttypes/data.html", {'children': self.getChildren().sort_by_orderpos(), 'node': self}, macro="show_node_image")


    def show_node_text(self, words=None, language=None, separator="", labels=0):
        return self.show_node_text_deep(words=words, language=language, separator=separator, labels=labels)


    def show_node_text_deep(self, words=None, language=None, separator="", labels=0):

        def render_mask_template(node, mfs, words=None, separator="", skip_empty_fields=True):
            """
               mfs: [mask] + list_of_maskfields
            """
            res = []
            exception_count = {}
            mask = mfs[0]
            for node_attribute, fd in mfs[1:]:
                metafield_type = fd['metafield_type']
                field_type = fd['field_type']
                if metafield_type in ['date', 'url', 'hlist']:
                    exception_count[metafield_type] = exception_count.setdefault(metafield_type, 0) + 1
                    value = node.get(node_attribute)
                    try:
                        value = fd['metadatatype'].getFormatedValue(fd['element'], node, language=language, mask=mask)[1]
                    except:
                        value = fd['metadatatype'].getFormatedValue(fd['element'], node, language=language)[1]
                elif metafield_type in ['field']:
                    if field_type in ['hgroup', 'vgroup']:
                        _sep = ''
                        if field_type == 'hgroup':
                            fd['unit'] = ''  # unit will be taken from definition of the hgroup
                            use_label = False
                        else:
                            use_label = True
                        value = getMetadataType(field_type).getViewHTML(
                                                                         fd['field'],  # field
                                                                         [node],  # nodes
                                                                         0,  # flags
                                                                         language=language,
                                                                         mask=mask, use_label=use_label)
                else:
                    value = node.get(node_attribute)
                    metadatatype = fd['metadatatype']

                    if hasattr(metadatatype, "language_snipper"):
                        metafield = fd['element']
                        if (metafield.get("type") == "text" and metafield.get("valuelist") == "multilingual") \
                            or \
                           (metafield.get("type") in ['memo', 'htmlmemo'] and metafield.get("multilang") == '1'):
                            value = metadatatype.language_snipper(value, language)

                    if value.find('&lt;') >= 0:
                        # replace variables
                        for var in re.findall(r'&lt;(.+?)&gt;', value):
                            if var == "att:id":
                                value = value.replace("&lt;" + var + "&gt;", unicode(node.id))
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
                                value = value.replace("<" + var + ">", unicode(node.id))
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

        lookup_key = make_lookup_key(self, language, labels)

        # if the lookup_key is already in the cache dict: render the cached mask_template
        # else: build the mask_template

        if lookup_key in maskcache:
            mfs = maskcache[lookup_key]
            res = render_mask_template(self, mfs, words=words, separator=separator)
            maskcache_accesscount[lookup_key] += 1
        else:
            mask = self.metadatatype.get_mask(u"nodesmall")
            for m in self.metadatatype.filter_masks(u"shortview", language=language):
                mask = m

            if mask:
                mfs = [mask]  # mask fields
                fields = mask.getMaskFields(first_level_only=True)
                ordered_fields = sorted([(f.orderpos, f) for f in fields])
                for _, field in ordered_fields:
                    fd = {}  # field descriptor
                    fd['field'] = field
                    element = field.getField()
                    element_type = element.get('type')
                    field_type = field.get('type')

                    t = getMetadataType(element.get("type"))

                    fd['format'] = field.getFormat()
                    fd['unit'] = field.getUnit()
                    label = field.getLabel()
                    fd['label'] = label
                    default = field.getDefault()
                    fd['default'] = default
                    fd['default_has_tal'] = (default.find('tal:') >= 0)

                    fd['metadatatype'] = t
                    fd['metafield_type'] = element_type
                    fd['element'] = element
                    fd['field_type'] = field_type

                    def getNodeAttributeName(field):
                        metafields = [x for x in field.getChildren() if x.type == 'metafield']
                        if len(metafields) != 1:
                            # this can only happen in case of vgroup or hgroup
                            logg.error("maskfield %s zero or multiple metafield child(s)", field.id)
                            return field.name
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
                res = render_mask_template(self, mfs, words=words, separator=separator)

            else:
                res = '&lt;smallview mask not defined&gt;'

        return res


    @classmethod
    def isContainer(cls):
        return 0

    def getTreeIcon(self):
        return ""

    def isSystemType(self):
        return 0

    def get_name(self):
        return self.name

    def getTechnAttributes(self):
        return {}

    def has_object(self):
        return True

    def getFullView(self, language):
        """Gets the fullview mask for the given `language`.
        If no matching language mask is found, return a mask without language specification or None.
        :rtype: Mask
        """

        lang_mask = self.metadatatype.filter_masks(masktype=u"fullview", language=language).first()

        if lang_mask is not None:
            return lang_mask
        else:
            return self.metadatatype.filter_masks(masktype=u"fullview").first()

    def getSysFiles(self):
        return []

    def buildLZAVersion(self):
        logg.warn("no lza builder implemented")

    def getEditMenuTabs(self):
        menu = list()
        try:
            submenu = Menu("menuglobals", "..")
            menu.append(submenu)
        except TypeError:
            pass
        return ";".join([m.getString() for m in menu])

    def getDefaultEditTab(self):
        return "view"

    def getLabel(self, lang=None):
        return self.name


class Content(Data, SchemaMixin):

    """(Abstract) base class for all content node types.
    """
    pass


@check_type_arg_with_schema
class Other(Content):
    pass

