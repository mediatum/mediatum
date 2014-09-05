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
import os
import core.athana as athana
import core.config as config
import core.tree as tree

from core.styles import theme
from mediatumtal import tal

def loadThemes():

    def manageThemes(themepath, type):
        name = config.get("config.theme", "")
        if os.path.exists(config.basedir+"/"+themepath+"themes/"+name+"/"):
            athana.addFileStore("/theme/", themepath+"themes/"+name+"/")
            athana.addFileStorePath("/css/", themepath+"themes/"+name+"/css/")
            athana.addFileStorePath("/img/", themepath+"themes/"+name+"/img/")
            athana.addFileStorePath("/js/", themepath+"themes/"+name+"/js/")
            theme.update(name, themepath+"themes/"+name+"/", type)
            print "Loading theme '%s' (%s)" %(name, type)

    if config.get("config.theme", "")!="":
        manageThemes("web/", "intern") # internal theme

        for k,v in config.getsubset("plugins").items(): # themes from plugins
            manageThemes(v, "extern")
    else:
        print "Loading default theme"


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

        if config.get('services.'+servicename +'.activate', "").lower()=="false":
            return
        if servicename + '.basecontext' in config.getsubset("services").keys():
            basecontext = config.getsubset("services")[servicename + '.basecontext']
        else:
            basecontext = config.get("services.contextprefix", "services")+'/'+servicename
        basecontext = ('/' + basecontext).replace('//', '/').replace('//', '/')
        context = athana.addContext(basecontext, ".")
        file = context.addFile(servicedir + "services/" + servicename)

        if  hasattr(file.m, "request_handler"):
            file.addHandler("request_handler").addPattern("/.*")

            if not os.path.exists(servicedata):
                try:
                    os.makedirs(servicedata)
                    os.makedirs(os.path.join(servicedata, "cache"))
                except OSError:
                    return

    if config.get("services.activate", "").lower()=="true":
        # try loading services from mediatum web/services/ folder
        p = config.basedir+"/web/services/"
        for servicedir in [f for f in os.listdir(p) if os.path.isdir(os.path.join(p, f))]:
            manageService(servicedir, "web/", os.path.join(datapath, servicedir))

        # try loading services from all plugins services/ folder
        for k,v in config.getsubset("plugins").items():
            p = os.path.join(config.basedir, v, 'services')
            if os.path.exists(p):
                for servicedir in [f for f in os.listdir(p) if os.path.isdir(os.path.join(p, f))]:
                    manageService(servicedir, v, os.path.join(datapath, k, servicedir))

    else:
        print "web services not activated"


def initContexts():
    athana.setBase(".")
    athana.setTempDir(config.get("paths.tempdir", "/tmp/"))
    from core.config import resolve_filename
    from core.translation import translate
    from core.ftp import collection_ftpserver
    tal.set_base(".")
    tal.add_macro_resolver(resolve_filename)
    tal.add_translator(translate)

    context = athana.addContext("/", ".")
    # === public area ===
    file = context.addFile("web/frontend/streams.py")
    file.addHandler("send_image").addPattern("/images/.*")
    file.addHandler("send_thumbnail").addPattern("/thumbs/.*")
    file.addHandler("send_thumbnail2").addPattern("/thumb2/.*")
    file.addHandler("send_doc").addPattern("/doc/.*")
    file.addHandler("send_file").addPattern("/file/.*")
    file.addHandler("send_file_as_download").addPattern("/download/.*")
    file.addHandler("send_attachment").addPattern("/attachment/.*")
    file.addHandler("send_attfile").addPattern("/attfile/.*")
    file.addHandler("get_archived").addPattern("/archive/.*")
    file.addHandler("get_root").addPattern("/[a-z,0-9,-]*\.[a-z]*") # root directory added /web/root (only files with extensions)

    file = context.addFile("web/frontend/zoom.py")
    file.addHandler("send_imageproperties_xml").addPattern("/tile/[0-9]*/ImageProperties.xml")
    file.addHandler("send_tile").addPattern("/tile/[0-9]*/[^I].*")

    #file = context.addFile("web/frontend/flippage.py")
    #file.addHandler("send_bookconfig_xml").addPattern("/[0-9]*/bookconfig.xml")
    #file.addHandler("send_page").addPattern("/[0-9]*/page/[0-9]*\.jpg")

    # === workflow ===
    #file = context.addFile("web/publish/main.py")
    #file.addHandler("publish").addPattern("/publish/.*")

    main_file = file = context.addFile("web/frontend/main.py")
    handler = file.addHandler("display")
    handler.addPattern("/")
    handler.addPattern("/node")
    file.addHandler("display_noframe").addPattern("/mask")
    file.addHandler("xmlsearch").addPattern("/xmlsearch")
    file.addHandler("jssearch").addPattern("/jssearch")
    file.addHandler("show_parent_node").addPattern("/pnode")
    file.addHandler("publish").addPattern("/publish/.*")
    file = context.addFile("web/frontend/popups.py")
    file.addHandler("popup_metatype").addPattern("/metatype/.*")
    file.addHandler("popup_fullsize").addPattern("/fullsize")
    file.addHandler("popup_thumbbig").addPattern("/thumbbig")
    #file.addHandler("show_index").addPattern("/popup_index")
    file.addHandler("show_help").addPattern("/popup_help")
    file.addHandler("show_attachmentbrowser").addPattern("/attachmentbrowser")
    file.addHandler("show_printview").addPattern("/print/.*")

    file = context.addFile("web/frontend/shoppingbag.py")
    file.addHandler("shoppingbag_action").addPattern("/shoppingbag")

    file = context.addFile("web/frontend/login.py")
    file.addHandler("login").addPattern("/login")
    file.addHandler("logout").addPattern("/logout")
    file.addHandler("pwdforgotten").addPattern("/pwdforgotten")
    file.addHandler("pwdchange").addPattern("/pwdchange")

    file = context.addFile("web/frontend/userdata.py")
    file.addHandler("show_user_data").addPattern("/user")

    file = context.addFile("workflow/diagram/__init__.py")
    file.addHandler("send_workflow_diagram").addPattern("/workflowimage")

    # === admin area ===
    context = athana.addContext("/admin", ".")
    file = context.addFile("web/admin/main.py")
    file.addHandler("show_node").addPattern("/(?!export/).*")
    file.addHandler("export").addPattern("/export/.*")

    # === edit area ===
    context = athana.addContext("/edit", ".")
    file = context.addFile("web/edit/edit.py")
    handler = file.addHandler("frameset")
    handler.addPattern("/")
    handler.addPattern("/edit")
    file.addHandler("showtree").addPattern("/edit_tree")
    file.addHandler("error").addPattern("/edit_error")
    file.addHandler("buttons").addPattern("/edit_buttons")
    file.addHandler("content").addPattern("/edit_content")
    file.addHandler("content").addPattern("/edit_content/.*")
    file.addHandler("action").addPattern("/edit_action")

    # === ajax tree ===
    context = athana.addContext("/ftree", ".")
    handler.addPattern("/ftree")
    file = context.addFile("web/ftree/ftree.py")
    file.addHandler("ftree").addPattern("/.*")

    # === services handling ===
    loadServices()

    # === OAI ===
    context = athana.addContext("/oai/", ".")
    file = context.addFile("export/oai.py")
    file.addHandler("oaiRequest").addPattern(".*")

    # === Export ===
    context = athana.addContext("/export", ".")
    file = context.addFile("export/export.py")
    file.addHandler("export").addPattern("/.*")

    # === static files ===
    athana.addFileStore("/ckeditor/", "lib/CKeditor/files.zip")
    athana.addFileStore("/css/", "web/css/")
    athana.addFileStore("/xml/", "web/xml/")
    athana.addFileStore("/img/", ["web/img/", "web/admin/img/", "web/edit/img/"])
    athana.addFileStore("/js/", ["web/js/", "js", "lib/CKeditor/js/"])


    # === last: path aliasing for collections ===
    handler = main_file.addHandler("display_alias")
    handler.addPattern("/[-.~_/a-zA-Z0-9]+$")

    # 404
    handler = main_file.addHandler("display_404")
    handler.addPattern("/(.)+$")

    # === theme handling ===
    loadThemes()

    # === frontend modules handling ===
    try:
        context = athana.addContext("/modules", ".")
        file = context.addFile("web/frontend/modules/modules.py")
        file.addHandler("getContent").addPattern("/.*")
    except IOError:
        print "no frontend modules found"

    #athana.addContext("/flush", ".").addFile("core/webconfig.py").addHandler("flush").addPattern("/py")

    # === check for ftp usage ===
    if config.get("ftp.activate","")=="true":
        athana.addFTPHandler(collection_ftpserver(None, port=int(config.get("ftp.port", 21)), debug=config.get("host.type", "testing"))) # dummy handler for users

        for collection in tree.getRoot("collections").getChildren():
            if collection.get("ftp.user") and collection.get("ftp.passwd"):
                athana.addFTPHandler(collection_ftpserver(collection, port=int(config.get("ftp.port", 21)), debug=config.get("host.type", "testing")))

def flush(req):
    athana.flush()
    import core.__init__ as c
    initContexts()
    import core.__init__
    print "all caches cleared"

def startWebServer():
    initContexts()
    athana.setThreads(int(config.get("host.threads","8")))
    z3950port = None
    if config.get('z3950.activate','').lower()=='true':
        z3950port = int(config.get("z3950.port","2021"))
    athana.run(int(config.get("host.port","8081")), z3950port)

