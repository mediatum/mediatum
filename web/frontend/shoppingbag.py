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
import logging
import codecs
from core.transition import httpstatus
import core.tree as tree
import core.users as users
from core.tree import db
from core.translation import lang
from core.acl import AccessData
from core.styles import theme
from schema.schema import VIEW_DATA_ONLY
from utils.utils import format_filesize
from utils.pathutils import isDescendantOf


WIDTH = 102
HEIGHT = 102
HEADER_HEIGHT = 100
FOOTER_HEIGHT = 0


logg = logging.getLogger(__name__)


def shoppingbag_action(req):

    if "clearall" in req.params.keys():
        req.session["shoppingbag"] = []

    if "action" in req.params:
        if req.params.get("action") == "add":  # add item in shoppingbag
            put_into_shoppingbag(req)
            return

        if req.params.get("action") == "delmsg":
            req.writeTALstr('<tal:block i18n:translate="popup_shoppingbag_object_delete"/>', {})
            return

        elif req.params.get("action") == "items":
            for key in req.params.keys():
                if key.startswith("del_"):  # delete item from list
                    for item in req.session["shoppingbag"]:
                        if item == key[4:-2]:
                            req.session["shoppingbag"].remove(key[4:-2])
                            show_shoppingbag(req)
                            return

                if key.startswith("do_export_zip"):  # export selected items in a zip-file
                    export_shoppingbag_zip(req)
                    show_shoppingbag(req)
                    return

                if key.startswith("do_export_bibtex"):  # export selected items in a bibtex-file
                    export_shoppingbag_bibtex(req)
                    show_shoppingbag(req)
                    return

        elif req.params.get("action") == "bags":
            user = users.getUserFromRequest(req)
            if req.params.get("operation") == "save_bag":
                user.addShoppingBag(req.params.get("bagname"), req.params.get("bagitems").split(","))
                show_shoppingbag(req)
                return

            if req.params.get("operation") == "load_bag":
                msg = ""
                if load_shoppingbagByKey(req) == 0:
                    msg = "error, bag not found."
                show_shoppingbag(req, msg)
                return

            for key in req.params.keys():

                if key.startswith("load_"):
                    sb = user.getShoppingBag(key[5:])
                    if len(sb) == 1:
                        req.session["shoppingbag"] = sb[0].getItems()
                        break

                if key.startswith("delete_"):
                    sb = user.getShoppingBag(key[7:])
                    if len(sb) == 1:
                        user.removeChild(sb[0])
                        break

                if key.startswith("share_"):
                    sb = user.getShoppingBag(key[6:])
                    if len(sb) == 1:
                        logg.debug("shoppingbag action %s %s", sb[0].id, sb[0].isShared())
                        if sb[0].isShared():
                            sb[0].stopShare()
                        else:
                            sb[0].createShareKey()
                        break

            show_shoppingbag(req)
            return

    # open shoppingbag
    show_shoppingbag(req)


def load_shoppingbagByKey(req):
    bagkey = req.params.get("bagkey", "")
    if bagkey == "":
        return 1
    for user in users.loadUsersFromDB():
        for c in user.getShoppingBag():
            if c.getSharedKey() == bagkey:
                req.session["shoppingbag"] = c.getItems()
                return 1

    candidates = db.getNodeIdByAttribute("key", bagkey)
    home_root = tree.getRoot("home")
    for cand in candidates:
        n = tree.getNode(cand)
        if not n.getContentType() == "shoppingbag":
            continue
        if isDescendantOf(n, home_root):
            req.session["shoppingbag"] = n.getItems()
            return 1

    return 0


def put_into_shoppingbag(req):
    """add item to shoppingbag"""
    files = req.params["files"].split(',')
    try:
        f = req.session["shoppingbag"]
    except:
        f = []

    err_count = 0
    for item in files:
        if item not in f:
            f.append(item)
        else:
            err_count += 1

    req.session["shoppingbag"] = f

    s = ""
    if len(files) > 1:
        s = "s"
    if err_count == 0:
        req.writeTALstr('<tal:block i18n:translate="shoppingbag_object%s_added"/>' % (s), {})
    else:
        req.writeTALstr('<tal:block i18n:translate="shoppingbag_object%s_still_added"/>' % (s), {})
    return httpstatus.HTTP_OK


def show_shoppingbag(req, msg=""):
    """open shoppingbag and show content"""
    img = False
    doc = False
    media = False

    (width, height) = calculate_dimensions(req)
    v = {"width": width, "height": height}
    f = []

    # deliver image dimensions of original
    def calc_dim(file):
        ret = ""
        try:
            w = int(file.get("width"))
            h = int(file.get("height"))
        except:
            return "padding:0px 0px;width:90px;height:90px;"

        if w > h:
            factor = 90.0 / w
            h = h * 90.0 / w
            w = 90
            ret += 'padding:%spx 0px;' % ustr(int((90 - h) / 2))
        else:
            w = w * 90.0 / h
            h = 90
            ret += 'padding:0px %spx;' % ustr(int((90 - w) / 2))
        return ret + 'width:%spx;height:%spx;' % (ustr(int(w)), ustr(int(h)))

    # deliver document file size
    def calc_size(file):
        for f in file.getFiles():
            if f.getType() == "document":
                return format_filesize(f.getSize())
        return ""

    def calc_length(file):
        try:
            return file.getDuration()
        except:
            return ""

    access = AccessData(req)

    sb = req.session.get("shoppingbag", [])
    sb = [nid for nid in sb if nid.strip()]
    for node in access.filter(tree.NodeList(sb)):
        if node.getCategoryName() == "image":
            img = True
        if node.getCategoryName() == "document":
            doc = True
        if node.getCategoryName() in ["audio", "video"]:
            media = True
        f.append(node)

    if len(f) != len(req.session.get("shoppingbag", [])) and msg == "":
        msg = "popup_shoppingbag_items_filtered"

    v["files"] = f
    v["image"] = img
    v["document"] = doc
    v["media"] = media
    v["img_perc_range"] = range(1, 11)
    v["img_pix_sizes"] = ["1600x1200", "1280x960", "1024x768", "800x600"]
    v["calc_dim"] = calc_dim
    v["calc_size"] = calc_size
    v["calc_length"] = calc_length
    user = users.getUserFromRequest(req)
    v["shoppingbags"] = user.getShoppingBag()
    v["user"] = user
    v["msg"] = msg

    req.writeTAL(theme.getTemplate("shoppingbag.html"), v, macro="shoppingbag")
    return httpstatus.HTTP_OK


def export_shoppingbag_bibtex(req):
    """
    Export the metadata of selected nodes in a BibTeX-format
    """
    from web.frontend.streams import sendBibFile
    from schema.schema import getMetaType
    import core.config as config
    import random
    import os

    items = []  # list of nodes to be exported
    for key in req.params.keys():
        if key.startswith("select_"):
            items.append(key[7:])

    dest = config.get("paths.tempdir") + ustr(random.random()) + ".bib"

    with codecs.open(dest, "a", encoding='utf8') as f:
        for item in items:
            node = tree.getNode(item)
            mask = getMetaType(node.getSchema()).getMask("bibtex")
            if mask is not None:
                f.write(mask.getViewHTML([node], flags=8))  # flags =8 -> export type
            else:
                f.write("The selected document type doesn't have any bibtex export mask")
            f.write("\n")

    if len(items) > 0:
        sendBibFile(req, dest)
        for root, dirs, files in os.walk(dest, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
        if os.path.isdir(dest):
            os.rmdir(dest)


def export_shoppingbag_zip(req):
    from web.frontend.streams import sendZipFile
    from utils.utils import join_paths
    import core.config as config
    import random
    import os

    access = AccessData(req)

    items = []
    for key in req.params.keys():
        if key.startswith("select_"):
            _nid = key[7:]
            _n = tree.getNode(_nid)
            if access.hasAccess(_n, 'read'):
                items.append(_nid)

    dest = join_paths(config.get("paths.tempdir"), ustr(random.random())) + "/"

    # images
    if req.params.get("type") == "image":
        if req.params.get("metadata") in ["no", "yes"]:

            format_type = req.params.get("format_type")

            processtype = ""
            processvalue = ""
            if format_type == "perc":
                processtype = "percentage"
                _perc = req.params.get("img_perc", ";").split(";")
                if _perc[0] != "":
                    processvalue = _perc[0]
                else:
                    processvalue = int(_perc[1])

            elif format_type == "pix":
                processtype = "pixels"
                _pix = req.params.get("img_pix", ";;").split(";")
                if _pix[0] != "":
                    processvalue = _pix[0]
                else:
                    processvalue = int(_pix[1])

            elif format_type == "std":
                processtype = "standard"
                processvalue = req.params.get("img_pix", ";;").split(";")[2]

            for item in items:
                node = tree.getNode(item)
                if not access.hasAccess(node, 'data'):
                    continue
                if node.processImage(processtype, processvalue, dest) == 0:
                    logg.error("image not found")

    # documenttypes
    if req.params.get("type") == "document":
        if req.params.get("metadata") in ["no", "yes"]:
            if not os.path.isdir(dest):
                os.mkdir(dest)

            for item in items:
                node = tree.getNode(item)
                if not access.hasAccess(node, 'data'):
                    continue
                if node.processDocument(dest) == 0:
                    logg.error("document not found")

    # documenttypes
    if req.params.get("type") == "media":
        if req.params.get("metadata") in ["no", "yes"]:
            if not os.path.isdir(dest):
                os.mkdir(dest)

            for item in items:
                node = tree.getNode(item)
                if not access.hasAccess(node, 'data'):
                    continue
                if node.processMediaFile(dest) == 0:
                    logg.error("file not found")

    # metadata
    def flatten(arr):
        return sum(
            map(lambda a: flatten(a) if (a and isinstance(a[0], list) and a != "") else [a], [a for a in arr if a not in['', []]]), [])

    if req.params.get("metadata") in ["yes", "meta"]:
        for item in items:
            node = tree.getNode(item)
            if not access.hasAccess(node, 'read'):
                continue
            if not os.path.isdir(dest):
                os.mkdir(dest)

            content = {"header": [], "content": []}
            for c in flatten(node.getFullView(lang(req)).getViewHTML([node], VIEW_DATA_ONLY)):
                content["header"].append(c[0])
                content["content"].append(c[1])

            with codecs.open(dest + item + ".txt", "w", encoding='utf8') as f:
                f.write("\t".join(content["header"]) + "\n")
                f.write("\t".join(content["content"]) + "\n")

    if len(items) > 0:
        sendZipFile(req, dest)
        for root, dirs, files in os.walk(dest, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
        if os.path.isdir(dest):
            os.rmdir(dest)


def calculate_dimensions(session):
    try:
        files = session["shoppingbag"]
    except:
        files = []
    num = len(files)
    if num == 0:
        return 180, 160
    r = (num + 7) / 8
    if r < 2:
        r = 2
    width = r * WIDTH
    height = ((num + r - 1) / r) * HEIGHT + HEADER_HEIGHT + FOOTER_HEIGHT
    return (width, height)
