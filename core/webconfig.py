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
import core.athana as athana

def startWebServer():
    athana.setBase(".")
    athana.setTempDir("/tmp/")
    athana.addMacroResolver("core.config.resolve_filename")
    athana.addTranslator("core.translation.translate")

    context = athana.addContext("/", ".")

    # === public area ===
    file = context.addFile("web/frontend/streams.py")
    file.addHandler("send_image").addPattern("/images/.*")
    file.addHandler("send_image").addPattern("/images/.*")
    file.addHandler("send_thumbnail").addPattern("/thumbs/.*")
    file.addHandler("send_thumbnail2").addPattern("/thumb2/.*")
    file.addHandler("send_doc").addPattern("/doc/.*")
    file.addHandler("send_file").addPattern("/file/.*")
    file.addHandler("send_attachment").addPattern("/attachment/.*")
    file.addHandler("send_attfile").addPattern("/attfile/.*")
    file = context.addFile("web/frontend/treeframe.py")
    file.addHandler("treeframe").addPattern("/treeframe")
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
    file.addHandler("show_printview").addPattern("/print")
    file = context.addFile("web/frontend/login.py")
    file.addHandler("display_login").addPattern("/login")
    file.addHandler("login_submit").addPattern("/login_submit")
    file.addHandler("logout").addPattern("/logout")
    file.addHandler("display_changepwd").addPattern("/display_changepwd")
    file.addHandler("changepwd_submit").addPattern("/changepwd_submit")
    file = context.addFile("web/frontend/usersettings.py")
    file.addHandler("user_settings").addPattern("/user")

    # === admin area ===
    context = athana.addContext("/admin", ".")
    file = context.addFile("web/admin/main.py")
    file.addHandler("show_node").addPattern("/.*")
    file.addHandler("export").addPattern("/export/.*")
    #file = context.addFile("workflows.py")
    #file.addHandler("createWorkflowImage").addPattern("/workflowimage")

    # === edit area ===
    context = athana.addContext("/edit", ".")
    file = context.addFile("web/edit/edit.py")
    file.addHandler("frameset")
    handler.addPattern("/")
    handler.addPattern("/edit")
    file.addHandler("flush").addPattern("/flush")
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

    # === static files ===
    athana.addFileStore("/module/", "mod/FCKeditor/files.zip")
    athana.addFileStore("/css/", "web/css/")
    athana.addFileStore("/img/", ["web/img/", "img"])
    athana.addFileStore("/js/", ["web/js/", "js"])

    athana.setThreads(8)

    athana.run()

