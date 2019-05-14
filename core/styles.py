"""
 mediatum - a multimedia content repository

 Copyright (C) 2010 Arne Seifert <seiferta@in.tum.de>


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

import codecs
import logging
from mediatumtal import tal
import os
import attr
import core.config as config
from core import app
from core.transition import render_template, render_macro
import glob
from jinja2.loaders import FileSystemLoader, ChoiceLoader, PrefixLoader
from jinja2.exceptions import TemplateNotFound
from core.request_handler import addFileStore as _addFileStore
from core.request_handler import addFileStorePath as _addFileStorePath


full_styles_by_contenttype = {}
list_styles = {}


logg = logging.getLogger(__name__)


class Theme(object):

    def __init__(self, name, path):
        self.name = name
        self.path = path
        self.style_path = os.path.join(path, "styles")

    def getImagePath(self):
        return self.path + "/img/"

    def activate(self):
        import core.webconfig
        # XXX: this is ugly, is there a better way?
        core.webconfig.theme = self

        theme_jinja_loader = self.make_jinja_loader()
        if theme_jinja_loader is not None:
            logg.info("adding jinja loader for theme")
            app.add_template_loader(theme_jinja_loader, 0)

        _addFileStore("/theme/", self.path + "/")
        _addFileStorePath("/css/", self.path + "/css/")
        _addFileStorePath("/img/", self.path + "/img/")
        _addFileStorePath("/js/", self.path + "/js/")

    def get_tal_template_path(self, filename):
        raise NotImplementedError("implement in subclasses!")

    def getTemplate(self, filename):
        return self.get_tal_template_path(filename)

    def render_template(self, template_name, context):
        if template_name.endswith((".j2.jade", ".j2.html")):
            # caller wants a jinja template
            return render_template(template_name, **context)
        elif template_name.endswith(".html"):
            # caller wants a TAL template
            tal_template = self.get_tal_template_path(template_name)
            return tal.getTAL(tal_template, context)
        else:
            raise TemplateNotFound("invalid template name (must end with .j2.jade, .j2.html or .html): " + template_name)

    def render_macro(self, template_name, macro_name, context):
        if template_name.endswith((".j2.jade", ".j2.html")):
            # caller wants a jinja template
            return render_macro(template_name, macro_name, **context)
        elif template_name.endswith(".html"):
            # caller wants a TAL template
            tal_template = self.get_tal_template_path(template_name)
            return tal.getTAL(tal_template, context, macro=macro_name)
        else:
            raise TemplateNotFound("invalid template name (must end with .j2.jade, .j2.html or .html): " + template_name)


class DefaultTheme(Theme):

    PATH = "web/themes/mediatum"

    def __init__(self):
        super(DefaultTheme, self).__init__("default", DefaultTheme.PATH)

    @classmethod
    def make_jinja_loader(self):
        template_path = os.path.join(config.basedir, DefaultTheme.PATH, "templates")
        if os.path.isdir(template_path):
            return FileSystemLoader(template_path)

    @classmethod
    def get_tal_template_path(self, filename):
        relative_template_path = os.path.join(DefaultTheme.PATH, filename)
        if not os.path.exists(os.path.join(config.basedir, relative_template_path)):
            raise TemplateNotFound("TAL template {} not found".format(filename))

        return relative_template_path


class CustomTheme(Theme):

    def get_tal_template_path(self, filename):
        relative_template_path = self.path + filename
        if os.path.exists(os.path.join(config.basedir, relative_template_path)):
            return relative_template_path
        else:
            return DefaultTheme.get_tal_template_path(filename)

    def make_jinja_loader(self):
        template_path = os.path.join(config.basedir, self.path, "templates")
        default_jinja_loader = DefaultTheme.make_jinja_loader()
        prefix_default_loader = PrefixLoader({"mediatum": default_jinja_loader})

        if os.path.isdir(template_path):
            # This loader first looks  
            # at the CustomTheme template path, then the default template path, if nothing was found.
            return ChoiceLoader([
                prefix_default_loader,
                FileSystemLoader(template_path),
                default_jinja_loader
            ])
        else:
            # no template dir for this theme, only use templates from default theme
            return default_jinja_loader


class FullStyle(object):

    def __init__(self, path="", template=None, contenttype="all", name="name", label="label",
                 icon="icon", default="", description="", maskfield_separator=""):
        self.path = path
        self.type = type
        self.contenttype = contenttype
        self.name = name
        self.label = label
        self.icon = icon
        self.template = template
        self.default = default == "true"
        self.description = description
        self.maskfield_separator = maskfield_separator


class TALFullStyle(FullStyle):

    def render_template(self, req, context):
        template_path = os.path.join(self.path, self.template)
        return tal.getTAL(template_path, context, request=req)


class JinjaFullStyle(FullStyle):

    def render_template(self, req, context):
        template_path = os.path.join("styles", self.template)
        return render_template(template_path, **context)


@attr.s
class ListStyle(object):
    name = attr.ib()
    icon = attr.ib()
    label = attr.ib()
    path = attr.ib()
    template = attr.ib()
    description = attr.ib()
    maskfield_separator = attr.ib(default="")
    nodes_per_page = attr.ib(default=10, convert=int)

    def render_template(self, req, context):
        if self.template.endswith((".j2.jade", ".j2.html")):
            template_path = os.path.join("styles", self.template)
            return render_template(template_path, **context)
        else:
            template_path = os.path.join(self.path, self.template)
            return tal.getTAL(template_path, context, request=req)

def readStyleConfig(filename):
    attrs = {}

    with codecs.open(filename, "rb", encoding='utf8') as fi:
        for line in fi:
            if line.find("#") < 0:
                line = line.split("=")
                key = line[0].strip()
                value = line[1].strip().replace("\r", "").replace("\n", "")
                attrs[key] = value

    attrs["path"] = os.path.dirname(filename)
    return attrs


def make_style_from_config(attrs):
    style_type = attrs["type"]
    del attrs["type"]

    if style_type == "smallview":
        return ListStyle(**attrs)
    elif style_type == "bigview":
        template = attrs["template"]
        if template.endswith("j2.jade") or template.endswith("j2.html"):
            return JinjaFullStyle(**attrs)
        else:
            return TALFullStyle(**attrs)


def _load_styles_from_path(dirpath):
    full_styles_from_path = {}
    list_styles_from_path = {}

    if os.path.exists(dirpath):
        config_filepaths = glob.glob(dirpath + "/*.cfg")
        for filepath in config_filepaths:
            style_config = readStyleConfig(filepath)
            style = make_style_from_config(style_config)

            if isinstance(style, ListStyle):
                list_styles_from_path[style.name] = style
            else:
                styles_for_type = full_styles_from_path.setdefault(style.contenttype, {})
                styles_for_type[style.name] = style
    else:
        logg.warn("style path %s not found, ignoring", dirpath)

    return full_styles_from_path, list_styles_from_path


def _load_all_styles():
    from core import webconfig
    default_style_path = os.path.join(config.basedir, 'web/frontend/styles')
    default_full_styles, default_list_styles = _load_styles_from_path(default_style_path)
    theme_full_styles, theme_list_styles = _load_styles_from_path(webconfig.theme.style_path)

    # styles from a theme have higher priority
    full_styles_by_contenttype.update(default_full_styles)
    full_styles_by_contenttype.update(theme_full_styles)

    list_styles.update(default_list_styles)
    list_styles.update(theme_list_styles)


def get_list_style(style_name):
    if not list_styles:
        _load_all_styles()

    return list_styles.get(style_name)


def get_full_style(content_type, style_name):
    if not full_styles_by_contenttype:
        _load_all_styles()

    styles_for_content_type = full_styles_by_contenttype.get(content_type)
    if styles_for_content_type is None:
        raise Exception("no content styles defined for node type {}".format(content_type))

    return styles_for_content_type.get(style_name, styles_for_content_type.values()[0])


def get_styles_for_contenttype(content_type):
    if not full_styles_by_contenttype:
        _load_all_styles()

    return full_styles_by_contenttype.get(content_type, {}).values()
