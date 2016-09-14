"""
 mediatum - a multimedia content repository

 Copyright (C) 2010 Arne Seifert <seiferta@in.tum.de>

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
import os
from PIL import Image
from core.transition.athana_sep import athana_http as athana

import core.config as config
from utils.utils import CustomItem
from web.edit.edit_common import writetree
from core.transition import httpstatus
from core import Node
from core import db
from contenttypes import Collections

q = db.query
logg = logging.getLogger(__name__)


def getInformation():
    return {"version": "1.0", "system": 1}


def getContent(req, ids):
    if len(ids) > 0:
        ids = ids[0]

    node = q(Node).get(ids)

    if not node or node.type != "collections" or not node.has_write_access():
        req.setStatus(httpstatus.HTTP_FORBIDDEN)
        return req.getTAL("web/edit/edit.html", {}, macro="access_error")

    if "action" in req.params:
        if req.params.get("action") == "translate":
            # translation
            req.writeTALstr('<tal:block tal:content="key" i18n:translate=""/>', {"key": req.params.get("key")})

        if req.params.get("action") == "nodeselection":
            # tree popup for node selection
            def f(req, node, objnum, link, indent, type):
                indent *= 10
                nodename = node.name
                try:
                    nodename = node.getLabel()
                except:
                    logg.exception("exception in getContent, ignored")

                if type == 1:
                    link = u'{}{}'.format(req.makeSelfLink({"tree_unfold": u"",
                                                            "tree_fold": node.id}),
                                          u"#node{}".format(node.id))
                elif type == 2:
                    link = u'{}{}'.format(req.makeSelfLink({"tree_unfold": node.id,
                                                            "tree_fold": u""}),
                                          u"#node{}".format(node.id))

                v = {}
                v["id"] = node.id
                v["type"] = type
                v["link1"] = link
                v["indent"] = indent + 10
                v["nodename"] = nodename
                v["writeaccess"] = node.has_data_access()
                return req.getTAL("web/edit/modules/frontendparts.html", v, macro="edit_frontendparts_nodeselection")

            content = writetree(req, q(Collections).one(), f, "", openednodes=[], sessionkey="nodetree", omitroot=0)
            req.writeTAL("web/edit/modules/frontendparts.html", {"content": content}, macro="edit_frontendparts_nodepopup")

        if req.params.get("action") == "iconselection":
            # image popup for image selection
            icons = []
            for p in athana.getFileStorePaths("/img/"):
                for root, dirs, files in os.walk(os.path.join(config.basedir, p)):
                    for name in [f for f in files if (f.endswith(".gif") or f.endswith(".png") or f.endswith(".jpg"))]:
                        if "CVS" not in root and not "web/admin/img" in root and not "web/edit/img" in root:
                            try:
                                pic = Image.open(root + name)
                                dimension = "%sx%spx" % (pic.size)
                                icons.append((name, dimension))
                            except:
                                pass

            req.writeTAL("web/edit/modules/frontendparts.html", {"icons": icons}, macro="edit_frontendparts_iconpopup")
        return ""

    if "do_action" in req.params:
        c = do_action(req, node)
        if c != "":
            return c

    v = {}
    v["id"] = node.id
    v["header_content"] = req.getTAL(
        "web/edit/modules/frontendparts.html", {"items": node.getCustomItems("header"), "type": "header"}, macro="frontendparts_section")
    v["footer_left_content"] = req.getTAL("web/edit/modules/frontendparts.html",
                                          {"items": node.getCustomItems("footer_left"),
                                           "type": "footer_left"},
                                          macro="frontendparts_section")
    v["footer_right_content"] = req.getTAL("web/edit/modules/frontendparts.html",
                                           {"items": node.getCustomItems("footer_right"),
                                            "type": "footer_right"},
                                           macro="frontendparts_section")

    return req.getTAL("web/edit/modules/frontendparts.html", v, macro="edit_frontendparts")


def modifyItem(req, node, type, id):
    if id == -1:
        item = CustomItem("", "")
    else:
        item = node.getCustomItems(type)[id]
    v = {}
    files = []
    content_file = node.files.filter_by(filetype=u"content").scalar()
    if content_file is not None:
        startpage_descriptor = node.system_attrs.get("startpagedescr.html/" + content_file.base_name)
        if startpage_descriptor:
            files.append((content_file, startpage_descriptor))

    db.session.commit()

    v["item"] = item  # [id]
    v["files"] = files
    v["id"] = id
    v["type"] = type
    v["node"] = node
    v["item_types"] = ["intern", "text", "link", "node"]
    return req.getTAL("web/edit/modules/frontendparts.html", v, macro="edit_modify_item")


def do_action(req, node):
    actiontype = req.params.get("do_action")

    if actiontype in ["header", "footer_left", "footer_right"]:

        for key in req.params.keys():
            if key.startswith(actiontype + "_add"):
                return modifyItem(req, node, actiontype, -1)

            if key.startswith(actiontype + "_down"):
                items = node.get("system." + actiontype).split(";")
                p = int(key[len(actiontype) + 6:-2])
                p_0 = items[p]
                items[p] = items[p + 1]
                items[p + 1] = p_0
                node.set("system." + actiontype, ";".join(items))
                break

            if key.startswith(actiontype + "_up"):
                items = node.get("system." + actiontype).split(";")
                p = int(key[len(actiontype) + 4:-2])
                p_0 = items[p]
                items[p] = items[p - 1]
                items[p - 1] = p_0
                node.set("system." + actiontype, ";".join(items))
                break

            if key.startswith(actiontype + "_delete"):
                items = node.getCustomItems(actiontype)
                del items[int(key[len(actiontype) + 8:-2])]
                node.setCustomItems(actiontype, items)
                break

            if key.startswith(actiontype + "_edit"):
                return modifyItem(req, node, actiontype, int(key[len(actiontype) + 6:-2]))

            if key.startswith(actiontype + "_save"):
                item_type = req.params.get("input_type")
                items = node.getCustomItems(actiontype)
                ci = CustomItem(req.params.get("item_name"), req.params.get(
                    "item_" + item_type + '_value'), item_type, req.params.get("item_icon"))
                if req.params.get("item_id") == "-1":
                    # add
                    items.append(ci)
                else:
                    # update
                    items[int(req.params.get("item_id"))] = ci
                node.setCustomItems(actiontype, items)
                break
    return ""
