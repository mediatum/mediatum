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
import core.config as config
import core.tree as tree
import schema
import core.athana as athana
import core.acl as acl
import os

from utils.utils import getMimeType, format_filesize,splitfilename, u, EncryptionException, Menu
from core.tree import Node,FileNode
from schema.schema import loadTypesFromDB, VIEW_HIDE_EMPTY,VIEW_DATA_ONLY
from core.translation import lang
from lib.pdf import parsepdf
import default

fileicons = {'directory':'mmicon_dir.gif', 'application/pdf':'mmicon_pdf.gif', 'image/jpeg':'mmicon_jpg.gif', 'image/gif':'mmicon_gif.gif', 'image/png':'mmicon_png.gif', 'image/tiff':'mmicon_tiff.gif', 'image/x-ms-bmp':'mmicon_bmp.gif', 'application/postscript':'mmicon_ps.gif', 'application/zip':'mmicon_zip.gif', 'other':'mmicon_file.gif' , "back": "mmicon_back.gif", "application/mspowerpoint":"mmicon_ppt.gif", "application/msword":"mmicon_doc.gif", "video/x-msvideo":"mmicon_avi.gif"}

""" document class """
class Document(default.Default):

    def _prepareData(node, req, words=""):

        access = acl.AccessData(req)     
        mask = node.getMask("nodebig")

        obj = {}
        if mask:
            obj['metadata'] = mask.getViewHTML([node], VIEW_HIDE_EMPTY, lang(req)) # hide empty elements
        else:
            obj['metadata'] = []
        obj['node'] = node  
        obj['path'] = req and req.params.get("path","") or ""
        files, sum_size = node.filebrowser(req)
        
        #doc_exist = False
        #for f in node.getFiles():
        #    if f.type=="doc":
        #        doc_exist = True
            
        obj['attachment'] = files
        obj['sum_size'] = sum_size
        
        obj['bibtex'] = False
        if node.getMask("bibtex"):
            obj['bibtex'] = True
        
        if node.has_object():
            obj['canseeoriginal'] = access.hasAccess(node,"data")
            obj['documentlink'] = '/doc/'+str(node.id)+'/'+str(node.id)+'.pdf'
            obj['documentdownload'] = '/download/'+str(node.id)+'/'+str(node.id)+'.pdf'
        else:
            obj['canseeoriginal']= False
        obj['documentthumb'] = '/thumb2/'+str(node.id) 

        if "oogle" not in (req.get_header("user-agent") or ""):
            obj['print_url'] = '/print/'+str(node.id)
        else:
            #don't confuse search engines with the PDF link
            obj['print_url'] = None
            obj['documentdownload'] = None

        if "style" in req.params.keys():
            req.session["full_style"] = req.params.get("style", "full_standard")
        elif "full_style" not in req.session.keys():
            if "contentarea" in req.session.keys():
                col = req.session["contentarea"].collection
                req.session["full_style"] = col.get("style_full")
            else:
                req.session["full_style"] = "full_standard"
       
        obj['style'] = req.session["full_style"]
        return obj
     
    """ format big view with standard template """
    def show_node_big(node, req):
        return req.getTAL("contenttypes/document.html", node._prepareData(req), macro="showbig")
    
    """ format node image with standard template """
    def show_node_image(node):
        return '<img src="/thumbs/'+node.id+'" class="thumbnail" border="0"/>'
    
    def isContainer(node):
        return 0
    
    def has_object(node):
        for f in node.getFiles():
            if f.type=="doc" or f.type=="document":
                return True
        return False

    def getLabel(node):
        return node.name

    def getSysFiles(node):
        return ["doc","document","thumb", "thumb2","presentati", "presentation", "fulltext","fileinfo"]

       
    """ postprocess method for object type 'document'. called after object creation """
    def event_files_changed(node):
        print "Postprocessing node",node.id
        
        thumb = 0
        fulltext = 0
        doc = None
        present = 0
        fileinfo = 0
        for f in node.getFiles():
            if f.type == "thumb":
                thumb = 1
            elif f.type.startswith("present"):
                present = 1
            elif f.type == "fulltext":
                fulltext = 1
            elif f.type == "fileinfo":
                fileinfo = 1
            elif f.type == "doc":
                doc = f
            elif f.type == "document":
                doc = f

        if not doc:
            for f in node.getFiles():
                if f.type == "thumb":
                    node.removeFile(f)
                elif f.type.startswith("present"):
                    node.removeFile(f)
                elif f.type == "fileinfo":
                    node.removeFile(f)
                elif f.type == "fulltext":
                    node.removeFile(f)

        if doc:
            path,ext = splitfilename(doc.retrieveFile())

            if not (thumb and present and fulltext and fileinfo):
                thumbname = path+".thumb"
                thumb2name = path+".thumb2"
                fulltextname = path + ".txt"
                infoname = path + ".info"
                tempdir = config.get("paths.tempdir")
                try:
                    pdfdata = parsepdf.parsePDF2(doc.retrieveFile(), config.basedir, tempdir, thumbname, thumb2name, fulltextname, infoname)
                except parsepdf.EncryptedException:
                    print "*** encrypted ***"
                    raise EncryptionException()

                if not os.path.isfile(infoname):
                    raise "PostprocessingError"

                fi = open(infoname, "rb")
                for line in fi.readlines():
                    i = line.find(':')
                    if i>0:
                       node.set("pdf_"+line[0:i].strip().lower(), u(line[i+1:].strip()))
                fi.close()

                node.addFile(FileNode(name=thumbname, type="thumb", mimetype="image/jpeg"))
                node.addFile(FileNode(name=thumb2name, type="presentation", mimetype="image/jpeg"))
                node.addFile(FileNode(name=fulltextname, type="fulltext", mimetype="text/plain"))
                node.addFile(FileNode(name=infoname, type="fileinfo", mimetype="text/plain"))

    """ list with technical attributes for type document """
    def getTechnAttributes(node):
        return {"PDF":{"pdf_moddate":"Datum",
                "pdf_file size":"Dateigr&ouml;&szlig;e",
                "pdf_title":"Titel",
                "pdf_creationdate":"Erstelldatum",
                "pdf_author":"Autor",
                "pdf_pages":"Seitenzahl",
                "pdf_producer":"Programm",
                "pdf_pagesize":"Seitengr&ouml;&szlig;e",
                "pdf_creator":"PDF-Erzeugung",
                "pdf_encrypted":"Verschl&uuml;sselt",
                "pdf_tagged":"Tagged",
                "pdf_optimized":"Optimiert",
                "pdf_linearized":"Linearisiert",
                "pdf_version":"PDF-Version"},
                
                "Common":{"pdf_print":"druckbar",
                "pdf_copy":"Inhalt entnehmbar",
                "pdf_change":"&auml;nderbar",
                "pdf_addnotes":"kommentierbar"},

                "Standard":{"creationtime":"Erstelldatum",
                "creator":"Ersteller"}}

    """ show uploadform for metadatatype 'document' """
    def upload_form(node, req):
        req.writeTAL("contenttypes/document.html", {"metadatatypes": loadTypesFromDB()}, macro="uploadform")

    """ popup window for actual nodetype """
    def popup_fullsize(node, req):
        for f in node.getFiles():
            if f.getType() == "doc" or f.getType() == "document":
                req.sendFile(f.retrieveFile(), f.getMimeType())
                return

    """ get attachments for node (current directory) """
    def filebrowser(node, req):
        global fileicons
        filesize = 0
        ret = list()
        path = ""
        for f in node.getFiles():
            if f.getType() == "attachment":
                path = f._path
                break
        
        if path == "":
            # no attachment directory -> test for single file
            file = {}
            for f in node.getFiles():
                if f.getType() not in node.getSysFiles():
                    file["mimetype"], file["type"] = getMimeType(f.getName())
                    file["icon"] = fileicons[file["mimetype"]]
                    file["path"] = f._path
                    file["name"] = f.getName()
                    file["size"] = format_filesize(f.getSize())
                    filesize += f.getSize()
                    ret.append(file)
            return ret, filesize

        if not path.endswith("/") and not req.params.get("path", "").startswith("/"):
            path += "/"
        path += req.params.get("path", "")

        if req.params.get("path","")!="":
            file = {}
            file["type"] = "back"
            file["mimetype"] = "back"
            file["icon"] = fileicons[file["mimetype"]]
            file["name"] = ".."
            file["path"] = req.params.get("path", "")
            file["req_path"] = req.params.get("path", "")[:req.params.get("path", "").rfind("/")]
            ret.append(file)

        for name in os.listdir(config.settings["paths.datadir"] + path+"/"):
            
            if name.endswith(".thumb") or name.endswith(".thumb2"):
                continue
            file = {}

            file_path = os.path.join(config.settings["paths.datadir"] +path, name)
            if os.path.isdir(file_path):
                # directory
                file["type"] = "dir"
                file["mimetype"] = "directory"
            else:
                # file
                file["mimetype"], file["type"] = getMimeType(name)
                file["size"] = format_filesize(os.path.getsize(file_path))
                filesize += os.path.getsize(file_path)

            file["icon"] = fileicons[file["mimetype"]]
            file["path"] = os.path.join(path, name)
            file["name"] = name
            file["req_path"] = req.params.get("path", "") + "/" + file["name"]
            ret.append(file)

        return ret, format_filesize(filesize)

    """ format attachment browser """
    def getAttachmentBrowser(node, req):
        f, s = node.filebrowser(req)
        req.writeTAL("contenttypes/document.html", {"files":f, "sum_size":s, "id": req.params.get("id",""), "path":req.params.get("path", "")}, macro="attachmentbrowser")

        
    def getEditMenuTabs(node):
        menu = list()
        try:
            submenu = Menu("tab_layout", "description","#", "../") #new
            submenu.addItem("tab_view","tab_view")
            menu.append(submenu)
            
            submenu = Menu("tab_metadata", "description","#", "../") # new
            submenu.addItem("tab_metadata","tab_metadata")
            submenu.addItem("tab_files_obj","tab_files")
            submenu.addItem("tab_lza", "tab_lza")
            menu.append(submenu)
            
            submenu = Menu("tab_classes_header", "description","#", "../") # new
            submenu.addItem("tab_classes","tab_classes")
            menu.append(submenu)

            submenu = Menu("tab_security", "description","#", "../") # new
            submenu.addItem("tab_acls","tab_acls")
            menu.append(submenu)
            
        except TypeError:
            pass
        return menu

    def getDefaultEditTab(node):
        return "tab_view"
        