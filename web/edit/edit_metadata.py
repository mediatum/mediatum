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
    access = AccessData(req)
    reload_script = False
    faultydir = getFaultyDir(users.getUserFromRequest(req))
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
    idstr=""
    for id in ids:
        if idstr:
            idstr+=","
        node = tree.getNode(id)
        if len(nodes)==0 or nodes[0].type == node.type:
            nodes += [node]
        idstr+=id

    maskname = req.params.get("mask", node.get("edit.lastmask") or "editmask")
    node.set("edit.lastmask", maskname)
    mask = node.getType().getMask(maskname)

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

        nodes = mask.updateNode(nodes, req)
        for node in nodes:
            if hasattr(node,"event_metadata_changed"):
                node.event_metadata_changed()
            else:
                print formatException()
        
        errorlist = mask.validateNodelist(nodes)

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
        req.params["errorlist"] = mask.validate(nodes)

    masklist = []
    for m in node.getType().getMasks():
        if m.get("masktype")!="edit":
            continue
        masklist.append(m)

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

    req.writeTAL("web/edit/edit_metadata.html", {"reload_script":reload_script, "idstr":idstr, "masklist":masklist, "maskname":maskname, "maskform":mask.getFormHTML(nodes, req), "creation_date":creation_date, "update_date":update_date}, macro="edit_metadata")
