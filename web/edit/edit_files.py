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
import core.tree as tree
from utils.utils import formatTechAttrs,getMimeType
from utils.date import format_date
from utils.fileutils import importFile
import os
import core.users as users
import core.config as config
import logging
import core.acl as acl

allow_delete_unused = 0

def edit_files(req, ids):
    node = tree.getNode(ids[0])
    update_error = False
    access = acl.AccessData(req)
    if not access.hasWriteAccess(node):
        req.writeTAL("web/edit/edit.html", {}, macro="access_error")
        return

    mime = ""


    if req.params.get("postprocess","")!="":
        if hasattr(node,"event_files_changed"):
            try:
                node.event_files_changed()
            except "PostprocessingError":
                update_error = True

    if req.params.get("addfile","")!="":
        only_add = req.params.get("change_file", "no") == "no"

        user = users.getUserFromRequest(req)
        file = req.params.get("updatefile")

        for nfile in node.getFiles():
            if nfile.getType()=="original" or nfile.getType()=="doc":
                mime = nfile.getMimeType()

        if not file or file.filename=="":
            if not only_add:
                for nfile in node.getFiles():
                    node.removeFile(nfile)
        else:
            r = file.filename.lower()
            mimetype = "application/x-download"
            type = "file"
            
            mimetype, type = getMimeType(r)

            if mime!=mimetype and mime!="" and not only_add:
                req.writeTAL("web/edit/edit_files.html",{},macro="filetype_error")
            else:
                if not only_add:
                    for nfile in node.getFiles():
                        node.removeFile(nfile)

                logging.getLogger('usertracing').info(user.name + " upload "+file.filename+" ("+file.tempname+")")
                file = importFile(file.filename,file.tempname)
                if only_add and mime:
                    file.type = "extra"
                
                node.addFile(file)
                if hasattr(node,"event_files_changed"):
                    try:
                        node.event_files_changed()
                    except "PostprocessingError":
                        update_error = True
                    
        
    # delete attribute
    for key in req.params.keys():
        if key.startswith("attr_"):
            node.removeAttribute(key[5:-2])

    fields = node.getType().getMetaFields()
    fieldnames = []
    for field in fields:
        fieldnames +=[field.name]

    attrs = node.items()

    metafields={}
    technfields={}
    obsoletefields={}

    tattr = formatTechAttrs(node.getTechnAttributes())

    for key,value in attrs:
        if key in fieldnames:
            metafields[key]=formatdate(value, getFormat(fields, key))
        elif key in tattr.keys():
            technfields[key]=formatdate(value)
        else:
            obsoletefields[key]=value
    
    if req.params.get("type","")=="obsolete":
        print "delete obsolete"
        for key in obsoletefields:
             node.removeAttribute(key)
        obsoletefields={}

    elif req.params.get("type","")=="technical":
        print "delete technical"
        for key in technfields:
             node.removeAttribute(key)
        technfields={}

    req.writeTAL("web/edit/edit_files.html", {"id":req.params.get("id","0"), "tab":req.params.get("tab", ""), "node":node, "obsoletefields":obsoletefields, "allow_delete_unused":allow_delete_unused, "metafields":metafields, "fields":fields, "technfields":technfields, "tattr":tattr,"fd":formatdate, "gf":getFormat, "update_error":update_error}, macro="edit_files_file")


def getFormat(fields, name):
    for field in fields:
        if field.name == name:
            return field.getValues()


def formatdate(value, format=""):
    if format=="":
        format='%d.%m.%Y %H:%M:%S'
    try:
        return format_date(parse_date(value,"%Y-%m-%dT%H:%M:%S"), format=format)
    except:
        return value


