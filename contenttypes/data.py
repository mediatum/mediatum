# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import os as _os
import functools as _functools
import logging
import humanize
import math as _math
from warnings import warn

import flask as _flask

from mediatumtal import tal

import core as _core
import core.webconfig as _
from core.database.postgres.node import Node
from core.database.postgres.node import children_rel
import core.config as config
import core.translation as _core_translation
from core.styles import get_full_style
from core.postgres import check_type_arg_with_schema
from schema.schema import getMetadataType, VIEW_HIDE_EMPTY, SchemaMixin
from utils import utils as _utils_utils
from utils.utils import highlight
from markupsafe import Markup
from utils.strings import replace_attribute_variables

logg = logging.getLogger(__name__)

_default_thumbnail_paths = {}


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

        if metafield_type in ['date', 'url']:
            value = metatype.viewer_get_data(metafield, maskitem, mask, node, language)[1]

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
        res.append(fd["template"](value=value))

    return separator.join(res)


def get_thumbnail_size(width, height):
    scale = max(min(512 / width, 512 / height), _math.sqrt(65536 / (width * height)))
    return max(1, int(round(width*scale))), max(1, int(round(height*scale)))


def _get_node_attribute_name(maskitem):
    metafields = maskitem.children.filter_by(type=u"metafield").all()
    if len(metafields) != 1:
        # this can only happen in case of vgroup or hgroup
        logg.error("maskitem %s has zero or multiple metafield child(s)", maskitem.id)
        return maskitem.name
    return metafields[0].name


def _build_field_template(labels, field_descriptor):
    if labels:
        template = u"<b>{label}:</b> {value}"
    elif field_descriptor['node_attribute'].startswith("author"):
        template = u'<span class="author">{value}</span>'
    elif field_descriptor['node_attribute'].startswith("subject"):
        template = u'<b>{value}</b>'
    else:
        template = u"{value}"
    return _functools.partial(template.format, label=_utils_utils.esc(field_descriptor.get("label", "")))


def register_default_thumbnail_path(path, type_=None, schema=None):
    if (type_, schema) in _default_thumbnail_paths:
        raise RuntimeError(u"{} already exists!".format((type_, schema)))
    if not _os.path.isfile(path):
        raise RuntimeError(u"Default thumbnail '{}' does not exist!".format(path))
    _default_thumbnail_paths[(type_, schema)] = path


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

                    node_attribute = _get_node_attribute_name(maskitem)
                    fd['node_attribute'] = node_attribute

                    fd['template'] = _build_field_template(labels, fd)
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
    language = _core_translation.set_language(req.accept_languages)
    mask = node.getFullView(language)
    if mask is not None:
        return mask.getViewHTML([node], VIEW_HIDE_EMPTY, language)  # hide empty elements
    else:
        return _core_translation.translate_in_request("no_metadata_to_display", req)


def child_node_url(child_id, **kwargs):
    """XXX: this shouldn't be here, child display should not be a responsibility of content types!"""
    params = {k: v for k, v in _flask.request.args.items()}
    if "show_id" in params:
        params["show_id"] = child_id
    else:
        params["id"] = child_id

    params.update(kwargs)
    return _core.webconfig.node_url(**params)


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
            license_image_url = "/static/img/{}.png".format(license_name)

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

    if versions:
        if node.isActiveVersion():
            version = versions[-1]
        else:
            version, = (v for v in versions if v.transaction_id == node.transaction_id)
        ctx = {
            "node": node,
            "tag": version.tag,
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

    tree_icon_path = "/static/img/file.svg"

    def get_thumbnail_path(self):
        files = self.files.filter_by(filetype="thumbnail")
        for f in files:
            if f.exists:
                return f.abspath

        # looking in all img filestores for default thumb for this
        # a) node type and schema, or
        # b) schema, or
        # c) node type
        return _default_thumbnail_paths.get((self.type, None)) or \
               _default_thumbnail_paths.get((None, self.schema)) or \
               _default_thumbnail_paths.get((self.type, self.schema))

    def get_editor_menu(self, user, multiple_nodes, has_childs):
        menu = list(super(Content, self).get_editor_menu(user, multiple_nodes, has_childs))
        menuoperations = list(menu[1]["menuoperation"])
        menuoperations.insert(1, "changeschema")
        menuoperations.insert(2, { "menueditobject": ("classes", "moveobject", "copyobject", "deleteobject")})
        menu.insert(0, "parentcontent")
        menu.insert(2, "files")
        if not multiple_nodes:
            menuoperations.append("version")
            menu.insert(1, "view")
        menu[-1]["menuoperation"] = tuple(menuoperations)

        return tuple(menu)


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
