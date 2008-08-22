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

def initContexts():
    athana.setBase(".")
    athana.setTempDir("/tmp/")
    from core.config import resolve_filename
    from core.translation import translate
    from core.ftp import collection_ftpserver
    athana.addMacroResolver(resolve_filename)
    athana.addTranslator(translate)
    
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

    file = context.addFile("web/frontend/zoom.py")
    file.addHandler("send_imageproperties_xml").addPattern("/tile/[0-9]*/ImageProperties.xml")
    file.addHandler("send_tile").addPattern("/tile/[0-9]*/[^I].*")

    file = context.addFile("web/frontend/main.py")
    handler = file.addHandler("display")
    handler.addPattern("/")
    handler.addPattern("/node")
    file.addHandler("display_noframe").addPattern("/mask")
    file.addHandler("show_parent_node").addPattern("/pnode")
    file.addHandler("publish").addPattern("/publish/.*")
    file = context.addFile("web/frontend/popups.py")
    file.addHandler("popup_fullsize").addPattern("/fullsize")
    file.addHandler("put_into_shoppingbag").addPattern("/put_into_shoppingbag")
    file.addHandler("show_shoppingbag").addPattern("/popup_shoppingbag")
    file.addHandler("show_index").addPattern("/popup_index")
    file.addHandler("show_help").addPattern("/popup_help")
    file.addHandler("show_attachmentbrowser").addPattern("/attachmentbrowser")
    file.addHandler("show_printview").addPattern("/print/.*")
    file = context.addFile("web/frontend/login.py")
    file.addHandler("display_login").addPattern("/login")
    file.addHandler("login_submit").addPattern("/login_submit")
    file.addHandler("logout").addPattern("/logout")
    file.addHandler("display_changepwd").addPattern("/display_changepwd")
    file.addHandler("changepwd_submit").addPattern("/changepwd_submit")
    #file = context.addFile("web/frontend/usersettings.py")
    #file.addHandler("user_settings").addPattern("/user")

    file = context.addFile("workflow/workflow.py")
    file.addHandler("createWorkflowImage").addPattern("/workflowimage")

    #file = context.addFile("stats/contenttypes.py")
    #file.addHandler("contenttypes").addPattern("/contenttypes.png")
    #file = context.addFile("stats/dbstats.py")
    #file.addHandler("dbstats").addPattern("/dbstats")
    #file.addHandler("mimetypes").addPattern("/mimetypes.png")

    # === admin area ===
    context = athana.addContext("/admin", ".")
    file = context.addFile("web/admin/main.py")
    file.addHandler("show_node").addPattern("/.*")
    file.addHandler("export").addPattern("/export/.*")

    # === edit area ===
    context = athana.addContext("/edit", ".")
    file = context.addFile("web/edit/edit.py")
    handler = file.addHandler("frameset")
    handler.addPattern("/")
    handler.addPattern("/edit")
    #file.addHandler("flush").addPattern("/flush")
    file.addHandler("showtree").addPattern("/edit_tree")
    file.addHandler("error").addPattern("/edit_error")
    file.addHandler("buttons").addPattern("/edit_buttons")
    file.addHandler("content").addPattern("/edit_content")
    file.addHandler("action").addPattern("/edit_action")
    file = context.addFile("web/edit/edit_upload.py")
    file.addHandler("upload_new").addPattern("/upload_new")
    file = context.addFile("web/edit/edit_license.py")
    file.addHandler("objlist").addPattern("/objlist")

    # === OAI ===
    context = athana.addContext("/oai/", ".")
    file = context.addFile("export/oai.py")
    file.addHandler("oaiRequest").addPattern(".*")

    # === Exoprt ===
    context = athana.addContext("/export", ".")
    file = context.addFile("export/export.py")
    file.addHandler("export").addPattern("/.*")

    # === static files ===
    athana.addFileStore("/module/", "lib/FCKeditor/files.zip")
    athana.addFileStore("/css/", "web/css/")
    athana.addFileStore("/img/", ["web/img/", "img","web/admin/img/", "web/edit/img/"])
    athana.addFileStore("/js/", ["web/js/", "js"])

    #athana.addContext("/flush", ".").addFile("core/webconfig.py").addHandler("flush").addPattern("/py")
    
    for collection in tree.getRoot("collections").getChildren():
        if collection.get("ftp_user") and collection.get("ftp_passwd"):
            print "set up ftp server for collection", collection.getName()
            athana.addFTPHandler(collection_ftpserver(collection))
   
def flush(req):
    athana.flush()
    import core.__init__ as c
    initContexts()
    import core.__init__
    print "all caches cleared"

def startWebServer():
    initContexts()


    athana.setThreads(int(config.get("host.threads","8")))
    athana.run(int(config.get("host.port","8081")))

