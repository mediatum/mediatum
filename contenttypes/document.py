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
import default
from utils.utils import getMimeType, splitfilename, u, OperationException
from core.tree import Node,FileNode
from schema.schema import loadTypesFromDB, VIEW_HIDE_EMPTY,VIEW_DATA_ONLY
from core.translation import lang, t
from core.acl import AccessData
from core.styles import getContentStyles
from lib.pdf import parsepdf
from core.attachment import filebrowser
""" document class """
class Document(default.Default):
    def getTypeAlias(node):
        return "document"
        
    def getCategoryName(node):
        return "document"
    def _prepareData(node, req, words=""):
        access = acl.AccessData(req)
        mask = node.getFullView(lang(req))
        obj = {}
        if mask:
            obj['metadata'] = mask.getViewHTML([node], VIEW_HIDE_EMPTY, lang(req), mask=mask) # hide empty elements
        else:
            obj['metadata'] = []
        obj['node'] = node  
        obj['path'] = req and req.params.get("path","") or ""
        files, sum_size = filebrowser(node, req)
            
        obj['attachment'] = files
        obj['sum_size'] = sum_size
        
        obj['bibtex'] = False
        if node.getMask("bibtex"):
            obj['bibtex'] = True
        
        if node.has_object():
            obj['canseeoriginal'] = access.hasAccess(node,"data")
            if node.get('system.origname')=="1":
                obj['documentlink'] = '/doc/'+str(node.id)+'/'+node.getName()
                obj['documentdownload'] = '/download/'+str(node.id)+'/'+node.getName()
            else:
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
    def show_node_big(node, req, template="", macro=""):
        if template=="":
            styles = getContentStyles("bigview", contenttype=node.getContentType())
            if len(styles)>=1:
                template = styles[0].getTemplate()
        return req.getTAL(template, node._prepareData(req), macro)
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
            if f.type=="thumb":
                thumb = 1
            elif f.type.startswith("present"):
                present = 1
            elif f.type=="fulltext":
                fulltext = 1
            elif f.type=="fileinfo":
                fileinfo = 1
            elif f.type=="doc":
                doc = f
            elif f.type=="document":
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
                    pdfdata = parsepdf.parsePDF2(doc.retrieveFile(), tempdir)
                except parsepdf.PDFException, ex:
                    raise OperationException(ex.value)
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
    """ popup window for actual nodetype """
    def popup_fullsize(node, req):
        access = AccessData(req)
        if not access.hasAccess(node, "data") or not access.hasAccess(node,"read"):
            req.write(t(req, "permission_denied"))
            return
        
        for f in node.getFiles():
            if f.getType() == "doc" or f.getType() == "document":
                req.sendFile(f.retrieveFile(), f.getMimeType())
                return
                
    def popup_thumbbig(node, req):
        node.popup_fullsize(req)
        
    def getEditMenuTabs(node):
        return "menulayout(view);menumetadata(metadata;files;admin;lza);menuclasses(classes);menusecurity(acls)"
    def getDefaultEditTab(node):
        return "view"
        
    def processDocument(node, dest):
        for file in node.getFiles():
            if file.getType()=="document":
                filename = file.retrieveFile()
                if os.sep=='/':
                    cmd = "cp %s %s" %(filename, dest)
                    ret = os.system(cmd)
                else:
                    cmd = "copy %s %s" %(filename, dest+node.id+".pdf")
                    ret = os.system(cmd.replace('/','\\'))
        return 1
