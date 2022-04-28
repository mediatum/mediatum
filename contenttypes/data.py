# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import re
import logging
from warnings import warn
import humanize
import flask as _flask
from mediatumtal import tal

from core import Node, db
from core.database.postgres.node import children_rel
import core.config as config
from core.translation import lang, t
from core.styles import get_full_style
from core.postgres import check_type_arg_with_schema
from export.exportutils import default_context
from schema.schema import getMetadataType, VIEW_HIDE_EMPTY, SchemaMixin
from utils.utils import highlight
from utils.compat import iteritems, string_types
from markupsafe import Markup
from utils.strings import replace_attribute_variables
from core.request_handler import request_finished as _request_finished

logg = logging.getLogger(__name__)


# for TAL templates from mask cache
context = default_context.copy()
# XXX: does this work without hostname? Can we remove this?
context['host'] = "http://" + config.get("host.name", "")


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
        res = _flask.g.mediatum["maskcache"][lookup_key]
    except:
        res = (None, None)
    return res


def render_mask_template(node, mask, field_descriptors, language, words=None, separator="", skip_empty_fields=True):
    res = []

    for node_attribute, fd in field_descriptors:
        metafield_type = fd['metafield_type']
        maskitem = fd['maskitem']
        metafield = fd["metafield"]
        metatype = fd["metatype"]
        maskitem_type = fd["maskitem_type"]

        if metafield_type in ['date', 'url', 'hlist']:
            value = metatype.getFormattedValue(metafield, maskitem, mask, node, language)[1]

        elif metafield_type in ['field']:
            if maskitem_type in ['hgroup', 'vgroup']:
                _sep = ''
                if maskitem_type == 'hgroup':
                    fd['unit'] = ''  # unit will be taken from definition of the hgroup
                    use_label = False
                else:
                    use_label = True
                value = getMetadataType(maskitem_type).getViewHTML(
                    metafield,
                    [node],  # nodes
                    0,  # flags
                    language=language,
                    mask=mask, use_label=use_label)
        else:
            value = node.get_special(node_attribute)

            if value.find('&lt;') >= 0:
                # replace variables
                value = replace_attribute_variables(value, node.id, node.get_special, r'&lt;(.+?)&gt;', "&lt;", "&gt;")
                value = value.replace("&lt;", "<").replace("&gt;", ">")

            if value.find('<') >= 0:
                # replace variables
                value = replace_attribute_variables(value, node.id, node.get_special, r'\<(.+?)\>', "<", ">")
                value = value.replace("&lt;", "<").replace("&gt;", ">")

            default = fd['default']
            if not value and default:
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

    return separator.join(res)


class Data(Node):

    """Abstract base class for all node classes which can be viewed / fetched by frontend / api users.
    Methods in this class are concerned with viewing / representing the contents of the data node.

    In other words: Node classes which don't inherit from this class are seen as internal 'system types'.
    """

    content_children = children_rel("Content")

    editor_menu = (
        "parentcontent",
        "view",
        "metadata",
        "files",
        { "menuoperation": (
            "acls",
            "classes",
            "changeschema",
            { "menueditobject": (
                "moveobject",
                "copyobject",
                "deleteobject",
                )},
            "admin",
        )},
    )

    @classmethod
    def get_all_datatypes(cls):
        """Returns all known subclasses of cls except `Collections` and `Home`"""
        return cls.get_all_subclasses(filter_classnames=("collections", "home"))

    @classmethod
    def getTypeAlias(cls):
        """Returns an identifier for this content type, always lower case.
        By default, the class name in lowercase is used.
        """
        return cls.__name__.lower()

    @classmethod
    def get_original_filetype(cls):
        """Returns the File.filetype value for associated files that represent the "original" file
        """
        return "original"

    @classmethod
    def get_upload_filetype(cls):
        """Returns the File.filetype value that will be used by the editor for uploaded files.
        """
        return cls.__name__.lower()

    @classmethod
    def isContainer(cls):
        warn("use isinstance(node, Container) or issubclass(nodecls, Container)", DeprecationWarning)
        return 0

    @classmethod
    def get_default_edit_tab(cls):
        """Returns the editor tag that should be displayed when visiting a node.
        Defaults to the preview view
        """
        return "view"

    @property
    def has_upload_file(self):
        """Is True when the node has a file with type `self.get_upload_filetype`.
        """
        # XXX: should be scalar(), but we don't really try to avoid duplicates atm
        return self.files.filter_by(filetype=self.get_upload_filetype()).first() is not None

    def show_node_big(self, req, style_name=""):
        context = self._prepareData(req)
        style = get_full_style(self.type, style_name)
        return style.render_template(req, context)

    def show_node_image(self, language=None):
        return tal.getTAL(
            "contenttypes/data.html", {'children': self.getChildren().sort_by_orderpos(), 'node': self}, macro="show_node_image")

    def show_node_text(self, words=None, language=None, separator="", labels=0):
        return self.show_node_text_deep(words=words, language=language, separator=separator, labels=labels)

    def show_node_text_deep(self, words=None, language=None, separator="", labels=0):

        if not separator:
            separator = u"<br/>"

        lookup_key = make_lookup_key(self, language, labels)

        # if the lookup_key is already in the cache dict: render the cached mask_template
        # else: build the mask_template

        _flask.g.mediatum.setdefault("maskcache", {})

        if lookup_key in _flask.g.mediatum['maskcache']:
            mask, field_descriptors = _flask.g.mediatum['maskcache'][lookup_key]
            res = render_mask_template(self, mask, field_descriptors, language, words=words, separator=separator)

        else:
            mask = self.metadatatype.get_mask(u"nodesmall")
            for m in self.metadatatype.filter_masks(u"shortview", language=language):
                mask = m

            if mask:
                fields = mask.getMaskFields(first_level_only=True)
                ordered_fields = sorted([(f.orderpos, f) for f in fields])
                field_descriptors = []

                for _, maskitem in ordered_fields:
                    fd = {}  # field descriptor
                    fd['maskitem_type'] = maskitem.get('type')
                    fd['format'] = maskitem.getFormat()
                    fd['unit'] = maskitem.getUnit()
                    fd['label'] = maskitem.getLabel()
                    fd['maskitem'] = maskitem

                    default = maskitem.getDefault()
                    fd['default'] = default

                    metafield = maskitem.metafield
                    metafield_type = metafield.get('type')
                    fd['metafield'] = metafield
                    fd['metafield_type'] = metafield_type

                    t = getMetadataType(metafield_type)
                    fd['metatype'] = t

                    def getNodeAttributeName(maskitem):
                        metafields = maskitem.children.filter_by(type=u"metafield").all()
                        if len(metafields) != 1:
                            # this can only happen in case of vgroup or hgroup
                            logg.error("maskitem %s has zero or multiple metafield child(s)", maskitem.id)
                            return maskitem.name
                        return metafields[0].name

                    node_attribute = getNodeAttributeName(maskitem)
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
                    long_field_descriptor = (node_attribute, fd)
                    field_descriptors.append(long_field_descriptor)

                _flask.g.mediatum["maskcache"][lookup_key] = (mask, field_descriptors)
                res = render_mask_template(self, mask, field_descriptors, language, words=words, separator=separator)

            else:
                res = '&lt;smallview mask not defined&gt;'

        return res

    def get_name(self):
        return self.name

    def getTechnAttributes(self):
        return {}

    def has_object(self):
        return False

    @classmethod
    def get_sys_filetypes(cls):
        return []

    def getLabel(self, lang=None):
        return self.name


def _get_node_metadata_html(node, req):
    """Renders HTML data for displaying metadata using the the fullview mask.
    :rtype: unicode
    """
    language = lang(req)
    mask = node.getFullView(language)
    if mask is not None:
        return mask.getViewHTML([node], VIEW_HIDE_EMPTY, language)  # hide empty elements
    else:
        return t(req, "no_metadata_to_display")


def child_node_url(child_id, **kwargs):
    """XXX: this shouldn't be here, child display should not be a responsibility of content types!"""
    from core.webconfig import node_url
    params = {k: v for k, v in _flask.request.args.items()}
    if "show_id" in params:
        params["show_id"] = child_id
    else:
        params["id"] = child_id

    params.update(kwargs)
    return node_url(**params)


def get_license_urls(node):
    """Reads the `license` attribute of `node` and returns the license URL and license logo URL"""
    license_url = None
    license_image_url = None
    license = node.get("license")
    if license:
        parts = [p.strip() for p in license.split(",")]
        if len(parts) != 2:
            logg.warning("invalid license string '%s', must be comma-separated and contain 2 elements", license)
        elif not parts[1].startswith("http"):
            logg.warning("invalid license string '%s', second element must start with http", license)
        else:
            license_name, license_url = parts
            # XXX: hardcoded URL
            license_image_url = "/img/{}.png".format(license_name)

    return license_url, license_image_url


def get_metis_url(node):  # better: get_tracking_pixel_url(s)?
    """Reads the `metis_url` attribute of `node` and returns the metis URL"""
    metis_url = node.get("metis_url")
    if metis_url and not metis_url.startswith("http"):
        logg.warning("omitting invalid metis_url string '%s', must start with http", metis_url)
        metis_url = None

    return metis_url
    

def prepare_node_data(node, req):
    """Prepare data needed for displaying this object.
    :returns: representation dictionary
    :rtype: dict
    """

    if node.get('deleted') == 'true':
        # If this object is marked as deleted version, render the active version instead.
        active_version = node.getActiveVersion()
        data = prepare_node_data(active_version, req)
        data["version_deleted_html"] = Markup(tal.getTAL("web/frontend/styles/macros.html", data, macro="deleted_version_alert"))
        data["deleted"] = True
        return data

    data = {
        "deleted": False,
        "versions_html": "",
        "old_version_alert_html": "",
        "deleted_version_alert_html": "",
        "children_html": "",
        "metadata": Markup(_get_node_metadata_html(node, req)),
        "node": node,
        "path": req.args.get("path", "")
    }
    
    data["license_url"], data["license_image_url"] = get_license_urls(node)
    data["metis_url"] = get_metis_url(node)

    versions = node.tagged_versions.all()

    # a single version is ignored
    if len(versions) > 1:
        ctx = {
            "node": node,
            "tag": versions[-1].tag,
            "versions": versions,
        }
        data['versions_html'] = Markup(tal.getTAL("web/frontend/styles/macros.html", ctx, macro="object_versions"))
        if not node.isActiveVersion():
            data['old_version_alert_html'] = Markup(tal.getTAL("web/frontend/styles/macros.html", ctx, macro="old_version_alert"))

    children = node.children.filter_read_access().all()

    # XXX: this is a hack, remove child display from contenttypes!
    if children:
        # link to child detail in frontend and editor differ
        # hack: is this flask compatible?
        in_editor = req and req.mediatum_contextfree_path.startswith("/edit")
        if in_editor:
            get_detail_url = lambda srcnodeid, cid, pid: "?srcnodeid={}&id={}&pid={}".format(srcnodeid, cid, pid)
        else:
            get_detail_url = lambda srcnodeid, cid, pid: child_node_url(cid, srcnodeid=srcnodeid)

        data['children_html'] = tal.getTAL(
                "web/frontend/styles/macros.html",
                dict(
                    in_editor=in_editor,
                    children=children,
                    get_detail_url=get_detail_url,
                    srcnodeid=req.values.get("srcnodeid", ""),
                    parent=node,
                ),
                macro="bothView",
            )

    return data


class BadFile(Exception):
    """
    Raised if error while handling file
    """
    pass


class Content(Data, SchemaMixin):

    """(Abstract) base class for all content node types.
    """


@check_type_arg_with_schema
class Other(Content):

    def _prepareData(self, req):
        obj = prepare_node_data(self, req)
        if obj["deleted"]:
            # no more processing needed if this object version has been deleted
            # rendering has been delegated to current version
            return obj

        obj["naturalsize"] = humanize.filesize.naturalsize
        return obj
