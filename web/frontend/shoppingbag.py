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
import core
import core.tree as tree
from core.translation import lang
from schema.schema import VIEW_HIDE_EMPTY, VIEW_DATA_ONLY


WIDTH=102
HEIGHT=102
HEADER_HEIGHT=100
FOOTER_HEIGHT=0


def shoppingbag_action(req):

    if "action" in req.params:
        if req.params.get("action")=="add": # add item in shoppingbag
            put_into_shoppingbag(req)
            return
            
        elif req.params.get("action")=="items":
            for key in req.params.keys():
                if key.startswith("del_"): # delete item from list
                    for item in req.session["shoppingbag"]:
                        if item==key[4:-2]:
                            req.session["shoppingbag"].remove(key[4:-2])
                            show_shoppingbag(req)
                            return
                            
                if key.startswith("do_export"): # export selected items
                    export_shoppingbag(req)
                    show_shoppingbag(req)
                    return

    if "clearall" in req.params.keys():
        req.session["shoppingbag"] = []

    # open shoppingbag
    show_shoppingbag(req)

    
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
            err_count+=1

    req.session["shoppingbag"] = f
    if err_count==0:
        req.writeTALstr('<tal:block i18n:translate="shoppingbag_object_added"/>',{})
    else:
        req.writeTALstr('<tal:block i18n:translate="shoppingbag_object_still_added"/>',{})
    return athana.HTTP_OK

    
def show_shoppingbag(req):
    """open shoppingbag and show content"""
    img = False
    doc = False

    (width, height) = calculate_dimensions(req)
    v = {"width":width, "height":height}
    f = []
    
    def calc_dim(file):
        ret = ""
        w = int(file.get("width"))
        h = int(file.get("height"))
        
        if w>h:
            factor = 90.0/w
            h = h*90.0/w
            w = 90
            ret += 'padding:%spx 0px;' % str(int((90-h)/2))
        else:
            w = w*90.0/h
            h = 90
            ret += 'padding:0px %spx;' % str(int((90-w)/2))
        return ret +'width:%spx;height:%spx;' %(str(int(w)), str(int(h)))

    
    files = req.session.get("shoppingbag",[])

    for file in files:
        node = tree.getNode(file)
        if node.getContentType()=="image":
            img = True
        if node.getContentType() in("document", "dissertation"):
            doc = True
        f.append(node)

    v["files"] = f
    v["image"] = img
    v["document"] = doc
    v["img_perc_range"] = range(1,11)
    v["img_pix_sizes"] = ["1600x1200", "1280x960", "1024x768", "800x600"]
    v["calc_dim"] = calc_dim

    req.writeTAL("web/frontend/shoppingbag.html", v, macro="shoppingbag")
    return athana.HTTP_OK
    
def export_shoppingbag(req):
    from web.frontend.streams import sendZipFile
    from utils.utils import join_paths
    import core.config as config
    import random
    import os
    
    items = []
    for key in req.params.keys():
        if key.startswith("select_"):
            items.append(key[7:])
    
    dest = join_paths(config.get("paths.tempdir"), str(random.random())) + "/"
    
    if req.params.get("type")=="image":
        
        # images
        if req.params.get("metadata") in ["no", "yes"]:
        
            format_type = req.params.get("format_type")
            
            processtype = ""
            processvalue = ""
            if format_type=="perc":
                processtype = "percentage"
                _perc = req.params.get("img_perc", ";").split(";")
                if _perc[0]!="":
                    processvalue = _perc[0]
                else:
                    processvalue = int(_perc[1])

            elif format_type=="pix":
                processtype = "pixels"
                _pix = req.params.get("img_pix", ";;").split(";")
                if _pix[0]!="":
                    processvalue = _pix[0]
                else:
                    processvalue = int(_pix[1])
                
                
            elif format_type=="std":
                processtype = "standard"
                processvalue = req.params.get("img_pix", ";;").split(";")[2]

            
            for item in items:
                node = tree.getNode(item)
                
                ret = node.processImage(processtype, processvalue, dest)
                
                if ret==0:
                    print "image not found"
                
                
    # metadata
    if req.params.get("metadata") in ["yes", "meta"]:
        for item in items:
            node = tree.getNode(item)
            if not os.path.isdir(dest):
                os.mkdir(dest)
            
            content = {"header":[], "content":[]}
            for i in node.getFullView(lang(req)).getViewHTML([node], VIEW_DATA_ONLY):
                content["header"].append(i[0])
                content["content"].append(i[1])

            f = open(dest+item+".txt", "w")
            f.write("\t".join(content["header"])+"\n")
            f.write("\t".join(content["content"])+"\n")
            f.close()

    if len(items)>0:
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
    if num==0:
        return 180,160
    r = (num+7)/8
    if r < 2:
        r = 2
    width = r*WIDTH
    height = ((num+r-1) / r)*HEIGHT + HEADER_HEIGHT + FOOTER_HEIGHT
    return (width,height)

