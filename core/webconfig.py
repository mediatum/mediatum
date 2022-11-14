# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import logging
import os.path
import urllib

import flask as _flask
from mediatumtal import tal

import core.translation as _core_translation
import core.config as config
from core.styles import CustomTheme, DefaultTheme

from core.plugins import find_plugin_with_theme
import request_handler as _request_handler

logg = logging.getLogger(__name__)


global theme
theme = None


def init_theme():

    theme_name = config.get("config.theme", "")

    if theme_name:
        theme_basepath = find_plugin_with_theme(theme_name)

        if theme_basepath is None:
            logg.warning("theme from config file with name '%s' not found, maybe a plugin is missing?", theme_name)
            
        else:
            theme_dir = os.path.join(theme_basepath, "themes", theme_name)
            logg.info("Loading theme '%s' from '%s'", theme_name, theme_dir)
            theme = CustomTheme(theme_name, theme_dir + "/")
            theme.activate()
            return

    theme = DefaultTheme()
    theme.activate()
    logg.warning("using (broken) standard theme, you should create your own theme :)")


def node_url(nid=None, version=None, **kwargs):
    params = {}
    if "id" in kwargs:
        nid = kwargs.pop("id")
    if version:
        params["v"] = version
    params.update(kwargs)
    params = {k: unicode(v).encode("utf8") for k, v in params.items()}
    if params:
        return "/{}?{}".format(nid or "", urllib.urlencode(params))
    else:
        return "/" + str(nid)


def edit_node_url(nid=None, version=None, **kwargs):
    params = {}
    if "id" in kwargs:
        nid = kwargs.pop("id")
    if version:
        params["v"] = version
    params.update(kwargs)
    params = {k: unicode(v).encode("utf8") for k, v in params.items()}
    params["id"] = params["srcnodeid"] = nid or ""

    return "/edit/edit_content?srcnodeid={}&id={}&{}".format(nid or "", nid or "", urllib.urlencode(params))


def current_node_url(**kwargs):
    """Builds a new node URL from the current request params with values replaced by `kwargs`"""
    params = {k: v for k, v in _flask.request.args.items()}
    params.update(kwargs)
    return node_url(**params)


def add_template_globals():
    from core import app
    template_globals = dict(node_url=node_url, current_node_url=current_node_url)

    tal.add_template_globals(**template_globals)
    app.add_template_globals(**template_globals)
    app.add_template_globals(translate=_core_translation.translate_in_template)


def initContexts():
    _request_handler.setBase(config.basedir)
    _request_handler.setTempDir(config.get("paths.tempdir", "/tmp/"))
    from core.config import resolve_filename
    tal.set_base(config.basedir)
    tal.add_macro_resolver(resolve_filename)
    tal.add_translator(_core_translation.translate_in_template)
    add_template_globals()

    context = _request_handler.addContext("/", ".")

    workflows_enabled = config.getboolean("workflows.activate", True)
    admin_enabled = config.getboolean("admin.activate", True)
    edit_enabled = config.getboolean("edit.activate", True)
    oai_enabled = config.getboolean("oai.activate", False)

    # === public area ===
    filehandlers = context.addFile("web/frontend/filehandlers.py")
    filehandlers.addHandler("send_thumbnail").addPattern("/thumbnail/.*")
    filehandlers.addHandler("send_doc").addPattern("/doc/.*")
    filehandlers.addHandler("send_image").addPattern("/image/.*")
    filehandlers.addHandler("redirect_images").addPattern("/images/.*")
    handler = filehandlers.addHandler("send_file")
    handler.addPattern("/file/.*")
    handler.addPattern("/download/.*")
    filehandlers.addHandler("send_attfile").addPattern("/attfile/.*")
    filehandlers.addHandler("fetch_archived").addPattern("/archive/.*")

    main_file = file = context.addFile("web/frontend/main.py")
    handler = file.addHandler("display")
    handler.addPattern("/")
    handler.addPattern("/node")
    handler = file.addHandler("display_newstyle")
    handler.addPattern("/nodes/\d+")
    # /\d+ could also be a node, the handler must check this
    handler.addPattern("/\d+")

    if workflows_enabled:
        file.addHandler("workflow").addPattern("/mask")

    file.addHandler("show_parent_node").addPattern("/pnode")
    file.addHandler("publish").addPattern("/publish/.*")
    file = context.addFile("web/frontend/popups.py")
    file.addHandler("popup_metatype").addPattern("/metatype/.*")
    # file.addHandler("show_index").addPattern("/popup_index")
    file.addHandler("show_help").addPattern("/popup_help")
    file.addHandler("show_attachmentbrowser").addPattern("/attachmentbrowser")
    
    if config.getboolean("config.enable_printing"):
        file.addHandler("show_printview").addPattern("/print/\d+\.pdf")
        file.addHandler("redirect_old_printview").addPattern("/print/.*")

    file = context.addFile("web/frontend/login.py")
    file.addHandler("login").addPattern("/login")
    file.addHandler("logout").addPattern("/logout")
    file.addHandler("pwdforgotten").addPattern("/pwdforgotten")
    file.addHandler("pwdchange").addPattern("/pwdchange")

    if workflows_enabled:
        file = context.addFile("workflow/diagram/__init__.py")
        file.addHandler("send_workflow_diagram").addPattern("/workflowimage")

    if admin_enabled:
        context = _request_handler.addContext("/admin", ".")
        file = context.addFile("web/handlers/become.py")
        file.addHandler("become_user").addPattern("/_become/.*")
        file = context.addFile("web/admin/main.py")
        file.addHandler("show_node").addPattern("/(?!export/)(?!serverstatus/).*")
        file.addHandler("export").addPattern("/export/.*")
        file.addHandler("stats_server").addPattern("/serverstatus/.*")

    if edit_enabled:
        # === edit area ===
        context = _request_handler.addContext("/edit", ".")
        file = context.addFile("web/edit/edit.py")
        handler = file.addHandler("frameset")
        handler.addPattern("/")
        handler.addPattern("/edit")
        file.addHandler("edit_print").addPattern("/print/\d+_.+\.pdf")
        # file.addHandler("showtree").addPattern("/edit_tree")
        file.addHandler("edit_tree").addPattern("/treedata")
        file.addHandler("error").addPattern("/edit_error")
        # file.addHandler("buttons").addPattern("/edit_buttons")
        file.addHandler("content").addPattern("/edit_content")
        file.addHandler("content").addPattern("/edit_content/.*")
        file.addHandler("action").addPattern("/edit_action")

        # === ajax tree ===
        context = _request_handler.addContext("/ftree", ".")
        handler.addPattern("/ftree")
        file = context.addFile("web/ftree/ftree.py")
        file.addHandler("ftree").addPattern("/.*")

    # === services handling ===
    context = _request_handler.addContext("/services/export", ".")
    context.addFile("web/services/export.py").addHandler("request_handler").addPattern("/node/(?P<id>\d+).*")

    # === OAI ===
    if oai_enabled:
        context = _request_handler.addContext("/oai/", ".")
        file = context.addFile("export/oai.py")
        file.addHandler("oaiRequest").addPattern(".*")

    # === Export ===
    context = _request_handler.addContext("/export", ".")
    file = context.addFile("web/frontend/export.py")
    file.addHandler("export").addPattern("/.*")

    # === last: path aliasing for collections ===
    handler = main_file.addHandler("display_alias")
    handler.addPattern("/([_a-zA-Z][_/a-zA-Z0-9]+)$")

    # handle rest pattern
    filehandlers.addHandler("send_from_webroot").addPattern("/(.)+$")

    # testing global exception handler
    context = _request_handler.addContext("/_test", ".")
    file = context.addFile("web/handlers/handlertest.py")
    file.addHandler("error").addPattern("/error")
    file.addHandler("error_variable_msg").addPattern("/error_variable_msg")
    file.addHandler("db_error").addPattern("/db_error")
