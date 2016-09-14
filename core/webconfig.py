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
import logging
import os.path
import urllib
from mediatumtal import tal
import core.athana as athana
import core.config as config
from core.styles import Theme
from core import db, app

from core.plugins import find_plugin_with_theme

logg = logging.getLogger(__name__)


global theme
theme = None


def loadThemes():

    def manageThemes(theme_name, theme_basepath, theme_type):
        global theme
        theme_dir = os.path.join(theme_basepath, "themes", theme_name)
        theme = Theme(theme_name, theme_dir + "/", theme_type)
        theme_jinja_loader = theme.make_jinja_loader()
        if theme_jinja_loader is not None:
            logg.info("adding jinja loader for theme")
            app.add_template_loader(theme_jinja_loader, 0)
            
        athana.addFileStore("/theme/", theme_dir + "/")
        athana.addFileStorePath("/css/", theme_dir + "/css/")
        athana.addFileStorePath("/img/", theme_dir + "/img/")
        athana.addFileStorePath("/js/", theme_dir + "/js/")
        logg.info("Loading theme '%s' from '%s' (%s)", theme_name, theme_dir, theme_type)

    theme_name = config.get("config.theme", "")

    if theme_name:
        theme_basepath = find_plugin_with_theme(theme_name)

        if theme_basepath is None:
            logg.warn("theme from config file with name '%s' not found, maybe a plugin is missing?", theme_name)
        else:
            manageThemes(theme_name, theme_basepath, "extern")
            return

    # use fallback standard theme
    manageThemes("default", "web/", "intern")
    logg.warn("using (broken) standard theme, you should create your own theme :)", trace=False)


def loadServices():
    datapath = config.get("services.datapath", "")
    if not os.path.exists(os.path.join(datapath, "common")):
        try:
            os.makedirs(os.path.join(datapath, "common"))
        except OSError:
            pass

    def manageService(servicename, servicedir, servicedata):
        if not os.path.exists(servicedir + "services/" + servicename + "/__init__.py"):
            return

        if config.get('services.' + servicename + '.activate', "").lower() == "false":
            return
        if servicename + '.basecontext' in config.getsubset("services").keys():
            basecontext = config.getsubset("services")[servicename + '.basecontext']
        else:
            basecontext = config.get("services.contextprefix", u"services") + '/' + servicename
        basecontext = ('/' + basecontext).replace('//', '/').replace('//', '/')
        context = athana.addContext(str(basecontext), ".")
        file = context.addFile(servicedir + "services/" + servicename)

        if hasattr(file.m, "request_handler"):
            file.addHandler("request_handler").addPattern("/.*")

            if not os.path.exists(servicedata):
                try:
                    os.makedirs(servicedata)
                    os.makedirs(os.path.join(servicedata, "cache"))
                except OSError:
                    return

    if config.get("services.activate", "").lower() == "true":
        # try loading services from mediatum web/services/ folder
        p = config.basedir + "/web/services/"
        for servicedir in [f for f in os.listdir(p) if os.path.isdir(os.path.join(p, f))]:
            manageService(servicedir, "web/", os.path.join(datapath, servicedir))

        # try loading services from all plugins services/ folder
        for k, v in config.getsubset("plugins").items():
            p = os.path.join(config.basedir, v, 'services')
            if os.path.exists(p):
                for servicedir in [f for f in os.listdir(p) if os.path.isdir(os.path.join(p, f))]:
                    manageService(servicedir, v, os.path.join(datapath, k, servicedir))

    else:
        logg.info("web services not activated")


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


def current_node_url(**kwargs):
    """Builds a new node URL from the current request params with values replaced by `kwargs`"""
    from core.transition import request
    params = {k: v for k, v in request.args.items()}
    params.update(kwargs)
    return node_url(**params)


def add_template_globals():
    from core.translation import translate
    template_globals = dict(node_url=node_url, 
                            current_node_url=current_node_url, 
                            _t=translate)

    tal.add_template_globals(**template_globals)
    app.add_template_globals(**template_globals)


def initContexts():
    athana.setBase(config.basedir)
    athana.setTempDir(config.get("paths.tempdir", "/tmp/"))
    from core.config import resolve_filename
    from core.translation import translate, set_language
    from core.ftp import collection_ftpserver
    tal.set_base(config.basedir)
    tal.add_macro_resolver(resolve_filename)
    tal.add_translator(translate)
    add_template_globals()

    @athana.request_started
    def set_lang(req, *args):
        set_language(req)

    # XXX: init our temporary child count cahche
    from web.frontend import frame
    frame.init_child_count_cache()

    context = athana.addContext("/", ".")
    # === public area ===
    file = context.addFile("web/frontend/filehandlers.py")
    file.addHandler("send_thumbnail").addPattern("/thumbs/.*")
    file.addHandler("send_thumbnail2").addPattern("/thumb2/.*")
    file.addHandler("send_doc").addPattern("/doc/.*")
    file.addHandler("send_image").addPattern("/image/.*")
    file.addHandler("redirect_images").addPattern("/images/.*")
    handler = file.addHandler("send_file")
    handler.addPattern("/file/.*")
    handler.addPattern("/download/.*")
    file.addHandler("send_attachment").addPattern("/attachment/.*")
    file.addHandler("send_attfile").addPattern("/attfile/.*")
    file.addHandler("fetch_archived").addPattern("/archive/.*")
    file.addHandler("send_from_webroot").addPattern("/[a-z,0-9,-]*\.[a-z]*")  # root directory added /web/root (only files with extensions)

    file = context.addFile("web/frontend/zoom.py")
    file.addHandler("send_imageproperties_xml").addPattern("/tile/[0-9]*/ImageProperties.xml")
    file.addHandler("send_tile").addPattern("/tile/[0-9]*/[^I].*")

    main_file = file = context.addFile("web/frontend/main.py")
    handler = file.addHandler("display")
    handler.addPattern("/")
    handler.addPattern("/node")
    handler = file.addHandler("display_newstyle")
    handler.addPattern("/nodes/\d+")
    # /\d+ could also be a node, the handler must check this
    handler.addPattern("/\d+")
    file.addHandler("workflow").addPattern("/mask")
    file.addHandler("show_parent_node").addPattern("/pnode")
    file.addHandler("publish").addPattern("/publish/.*")
    file = context.addFile("web/frontend/popups.py")
    file.addHandler("popup_metatype").addPattern("/metatype/.*")
    file.addHandler("popup_fullsize").addPattern("/fullsize")
    file.addHandler("popup_thumbbig").addPattern("/thumbbig")
    # file.addHandler("show_index").addPattern("/popup_index")
    file.addHandler("show_help").addPattern("/popup_help")
    file.addHandler("show_attachmentbrowser").addPattern("/attachmentbrowser")
    
    if config.getboolean("host.enable_printing"):
        file.addHandler("show_printview").addPattern("/print/.*")

    file = context.addFile("web/frontend/login.py")
    file.addHandler("login").addPattern("/login")
    file.addHandler("logout").addPattern("/logout")
    file.addHandler("pwdforgotten").addPattern("/pwdforgotten")
    file.addHandler("pwdchange").addPattern("/pwdchange")

    file = context.addFile("workflow/diagram/__init__.py")
    file.addHandler("send_workflow_diagram").addPattern("/workflowimage")

    # === admin area ===
    context = athana.addContext("/admin", ".")
    file = context.addFile("web/handlers/become.py")
    file.addHandler("become_user").addPattern("/_become/.*")
    file = context.addFile("web/admin/main.py")
    file.addHandler("show_node").addPattern("/(?!export/).*")
    file.addHandler("export").addPattern("/export/.*")

    # === edit area ===
    context = athana.addContext("/edit", ".")
    file = context.addFile("web/edit/edit.py")
    handler = file.addHandler("frameset")
    handler.addPattern("/")
    handler.addPattern("/edit")
    # file.addHandler("showtree").addPattern("/edit_tree")
    file.addHandler("edit_tree").addPattern("/treedata")
    file.addHandler("error").addPattern("/edit_error")
    # file.addHandler("buttons").addPattern("/edit_buttons")
    file.addHandler("content").addPattern("/edit_content")
    file.addHandler("content").addPattern("/edit_content/.*")
    file.addHandler("action").addPattern("/edit_action")

    # === ajax tree ===
    context = athana.addContext("/ftree", ".")
    handler.addPattern("/ftree")
    file = context.addFile("web/ftree/ftree.py")
    file.addHandler("ftree").addPattern("/.*")

    # === help area ===
    context = athana.addContext("/help", '.')
    file = context.addFile("core/help.py")
    file.addHandler("getHelp").addPattern("/(?!img/).*")

    # === services handling ===
    loadServices()

    # === OAI ===
    context = athana.addContext("/oai/", ".")
    file = context.addFile("export/oai.py")
    file.addHandler("oaiRequest").addPattern(".*")

    # === Export ===
    context = athana.addContext("/export", ".")
    file = context.addFile("web/frontend/export.py")
    file.addHandler("export").addPattern("/.*")

    # === static files ===
    athana.addFileStore("/ckeditor/", "lib/CKeditor/files.zip")
    athana.addFileStore("/css/", "web/css/")
    athana.addFileStore("/xml/", "web/xml/")
    athana.addFileStore("/img/", ["web/img/", "web/admin/img/", "web/edit/img/"])
    athana.addFileStore("/js/", ["web/js/", "js", "lib/CKeditor/js/"])

    # === last: path aliasing for collections ===
    handler = main_file.addHandler("display_alias")
    handler.addPattern("/([_a-zA-Z][_/a-zA-Z0-9]+)$")

    # 404
    handler = main_file.addHandler("display_404")
    handler.addPattern("/(.)+$")

    # === theme handling ===
    loadThemes()

    # === check for ftp usage ===
    if config.get("ftp.activate", "") == "true":
        from contenttypes import Collections
        # dummy handler for users
        athana.addFTPHandler(collection_ftpserver(None, port=int(config.get("ftp.port", 21)), debug=config.get("host.type", "testing")))

        for collection in db.query(Collections).one().children:
            if collection.get("ftp.user") and collection.get("ftp.passwd"):
                athana.addFTPHandler(collection_ftpserver(
                    collection, port=int(config.get("ftp.port", 21)), debug=config.get("host.type", "testing")))

        db.session.close()

    # new admin area

    import web.newadmin
    athana.add_wsgi_context("/f/", web.newadmin.app)
    
    # testing global exception handler
    context = athana.addContext("/_test", ".")
    file = context.addFile("web/handlers/handlertest.py")
    file.addHandler("error").addPattern("/error")
    file.addHandler("error_variable_msg").addPattern("/error_variable_msg")
    file.addHandler("db_error").addPattern("/db_error")

def flush(req):
    athana.flush()
    import core.__init__ as c
    initContexts()
    import core.__init__
    logg.info("all caches cleared")
