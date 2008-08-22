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
from core.acl import AccessData
from edit_common import getFaultyDir,getHomeDir
import core.users as users
from utils.date import format_date,parse_date
from utils.utils import formatException
import core.tree as tree

import logging
from core.translation import lang, t

def edit_metadata(req, ids):

    user = users.getUserFromRequest(req)
    if "metadata" in users.getHideMenusForUser(user):
        req.writeTAL("web/edit/edit.html", {}, macro="access_error")
        return

    access = AccessData(req)
    reload_script = False
    faultydir = getFaultyDir(user)
    script = """\n<script language="javascript">
                  function openPopup(url, name, width, height)
                    {
                        var win1 = window.open(url,name,\'width=\'+width+\',height=\'+height+\',screenX=50,screenY=50,directories=no,location=no,menubar=no,scrollbars=no,status=no,toolbar=no,resizable=no\');
                        win1.focus();
                        return win1;
                    }

                  function handlelock(name)
                    {
                        if (document.getElementById('lock_'+name).checked){
                            document.getElementById(name).disabled = false;
                            document.getElementById(name).value = '';
                        }else{
                            document.getElementById(name).disabled = true;
                            document.getElementById(name).value = '? ';
                        }
                    }
                      </script>\n"""
    req.write(script)

    nodes = []
    idstr = ""
    for id in ids:
        if idstr:
            idstr+=","
        node = tree.getNode(id)
        if len(nodes)==0 or nodes[0].type == node.type:
            nodes += [node]
        idstr += id
    
    masklist = []
    for m in node.getType().getMasks(type="edit"):
        if access.hasReadAccess(m):
            masklist.append(m)

    if hasattr(node, "metaFields"):
                
        class SystemMask:
            def __init__(self, name, description, fields):
                self.name,self.description,self.fields = name,description,fields
            def getName(self):
                return self.name
            def getDescription(self):
                return self.description
            def getDefaultMask(self):
                return False
            def metaFields(self, lang=None):
                return self.fields
            def i_am_not_a_mask():
                pass
        masklist = [SystemMask("settings", t(req, "settings"), node.metaFields(lang(req)))] + masklist

    default = None
    for m in masklist:
        if m.getDefaultMask():
            default = m
            break
    if not default and len(masklist):
        default = masklist[0]

    maskname = req.params.get("mask", node.get("edit.lastmask") or "editmask")
    
    if maskname=="":
        maskname = default.getName()

    mask = None
    for m in masklist:
        if maskname == m.getName():
            mask = m
            break

    if not mask and default:
        mask = default
        maskname = default.getName()

    for n in nodes:
        n.set("edit.lastmask", maskname)

    if not mask:
        req.writeTAL("web/edit/edit_metadata.html", {}, macro="no_mask")
        return

    if "edit_metadata" in req.params:
        # check and save items

        userdir = getHomeDir(users.getUserFromRequest(req))

        for node in nodes:
            if not access.hasWriteAccess(node) or node.id == userdir.id:
                req.writeTAL("web/edit/edit.html", {}, macro="access_error")
                return

        logging.getLogger('usertracing').info(access.user.name + " change metadata "+idstr)

        user = users.getUserFromRequest(req)
        for node in nodes:
            node.set("updateuser", user.getName())
            node.set("updatetime", str(format_date()))

        if not hasattr(mask,"i_am_not_a_mask"):
            nodes = mask.updateNode(nodes, req)
            errorlist = mask.validateNodelist(nodes)
        else:
            for field in mask.metaFields():
                value = req.params.get(field.getName(), None)
                if value is not None:
                    for node in nodes:
                        node.set(field.getName(), value)
            errorlist = []

        if len(errorlist)>0:
            if "Speichern" in req.params:
                req.write('<p class="error">'+t(lang(req), "fieldsmissing") + '<br>')
                req.write(t(lang(req), 'saved_in_inconsistent_data')+'</p>')

        for node in nodes:
            if node.id in errorlist:
                faultydir.addChild(node)
                node.setAttribute("faulty", "true")
            else:
                faultydir.removeChild(node)
                node.removeAttribute("faulty")

        reload_script = True

    if "edit_metadata" in req.params or node.get("faulty")=="true":
        if not hasattr(mask, "i_am_not_a_mask"):
            req.params["errorlist"] = mask.validate(nodes)

    update_date = []
    if len(nodes)==1:
        for node in nodes:
            if node.get("updatetime"):
                try:
                    date = parse_date(node.get("updatetime"),"%Y-%m-%dT%H:%M:%S")
                    datestr = format_date(date, format='%d.%m.%Y %H:%M:%S')
                except:
                    datestr = node.get("updatetime")
                update_date.append([node.get("updateuser"),datestr])

    creation_date = []
    if len(nodes)==1:
        for node in nodes:
            if node.get("creationtime"):
                try:
                    date = parse_date(node.get("creationtime"),"%Y-%m-%dT%H:%M:%S")
                    datestr = format_date(date, format='%d.%m.%Y %H:%M:%S')
                except:
                    datestr = node.get("creationtime")
                creation_date.append([node.get("creator"), datestr])

    data = {}
    data["reload_script"] = reload_script
    data["idstr"] = idstr
    data["node"] = nodes[0]
    data["masklist"] = masklist
    data["maskname"] = maskname
    data["creation_date"] = creation_date
    data["update_date"] = update_date
    if not hasattr(mask,"i_am_not_a_mask"):
        data["maskform"] = mask.getFormHTML(nodes, req)
        data["fields"] = None
    else:
        data["maskform"] = None
        data["fields"] = mask.metaFields()
    req.writeTAL("web/edit/edit_metadata.html", data, macro="edit_metadata")
