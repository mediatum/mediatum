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

from utils.utils import getMimeType, format_filesize
#from date import *
from core.tree import Node,FileNode
from schema.schema import loadTypesFromDB, VIEW_HIDE_EMPTY,VIEW_DATA_ONLY
from core.translation import lang
from lib.pdf import parsepdf

fileicons = {'directory':'mmicon_dir.gif', 'application/pdf':'mmicon_pdf.gif', 'image/jpeg':'mmicon_jpg.gif', 'image/gif':'mmicon_gif.gif', 'image/png':'mmicon_png.gif', 'image/tiff':'mmicon_tiff.gif', 'image/x-ms-bmp':'mmicon_bmp.gif', 'application/postscript':'mmicon_ps.gif', 'application/zip':'mmicon_zip.gif', 'other':'mmicon_file.gif' , "back": "mmicon_back.gif", "application/mspowerpoint":"mmicon_ppt.gif", "application/msword":"mmicon_doc.gif", "video/x-msvideo":"mmicon_avi.gif"}

""" document class """
class Document(tree.Node):

    def _prepareData(node, req, words=""):

        access = acl.AccessData(req)       
        mask = node.getType().getMask("nodebig")
        obj = {}
        if mask:
            obj['metadata'] = mask.getViewHTML([node], VIEW_HIDE_EMPTY, lang(req)) # hide empty elements
        else:
            obj['metadata'] = []
        obj['node'] = node  
        obj['path'] = req and req.params.get("path","") or ""
        files, sum_size = node.filebrowser(req)
        obj['attachment'] = files
        obj['sum_size'] = sum_size
        obj['canseeoriginal'] = access.hasAccess(node,"data")

        if "oogle" not in req.request_headers.get("user-agent",""):
            obj['print_url'] = '/print/'+str(node.id)
        else:
            #don't confuse search engines with the PDF link
            obj['print_url'] = None

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
    
    """ format preview node text """
    def show_node_text(node, words=None, language=None, macro="metadatavalues"):
        metatext = list()
        mask = node.getType().getMask("nodesmall")
        if mask:
            for field in mask.getViewHTML([node], VIEW_DATA_ONLY):
                value = field[1]
                if words!=None:
                    value = highlight(value, words, '<font class="hilite">', "</font>")

                if value:
                    if field[0].startswith("author"):
                        value = '<span class="author">'+value+'</span>'
                    metatext.append(value)

        return athana.getTAL("contenttypes/document.html", {"values":metatext}, macro=macro, language=language)

    def can_open(node):
        return 0

    def getLabel(node):
        return node.name

    def getSysFiles(node):
        return ["doc","thumb","presentati","fulltext","fileinfo"]

       
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
            path,ext = splitfilename(doc.getPath())

            if not (thumb and present and fulltext and fileinfo):
                thumbname = path+".thumb"
                thumb2name = path+".thumb2"
                fulltextname = path + ".txt"
                infoname = path + ".info"
                tempdir = config.get("paths.tempdir")
                pdfdata = parsepdf.parsePDF2(doc.getPath(), config.basedir, tempdir, thumbname, thumb2name, fulltextname, infoname)

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
            if f.getType() == "doc":
                req.sendFile(f.getPath(), f.getMimeType())
                return

    """ get attachments for node (current directory) """
    def filebrowser(node, req):
        global fileicons
        filesize = 0
        ret = list()
        path = ""
        for f in node.getFiles():
            if f.getType() == "attachment":
                path = f.path
                break
        
        if path == "":
            # no attachment directory -> test for single file
            file = {}
            for f in node.getFiles():
                if f.getType() not in node.getSysFiles():
                    file["mimetype"], file["type"] = getMimeType(f.getName())
                    file["icon"] = fileicons[file["mimetype"]]
                    file["path"] = f.path
                    file["name"] = f.getName()
                    file["size"] = format_filesize(os.path.getsize(f.getPath()))
                    filesize += os.path.getsize(f.getPath())
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


