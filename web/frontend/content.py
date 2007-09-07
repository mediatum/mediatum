#!/bin/sh
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
import core.tree as tree
import os
import re

from utils.utils import getCollection,Link
from core.acl import AccessData
from web.frontend.searchresult import simple_search, extended_search

class Content:
    def feedback(self,req):
        pass
    def html(self,req):
        return ""

class SingleFile:
    def __init__(self,file,nr,num,words=None):
        self.attachment = None
        for f in file.getFiles():
            if f.getType()=="attachment":
                self.attachment = f
                break

        if not self.attachment:
            for f in file.getFiles():
                if f.getType() not in file.getSysFiles():
                    self.attachment = f
                    break


        self.datatype = file.getType()
        self.image = file.show_node_image()
        self.text = file.show_node_text(words)
        self.fields = self.datatype.getMetaFields()
        self.thumbnail = self.image
        self.node = file
        self.nr = nr
        self.num = num
        self.file = file
    def getLink(self):
        return '/node?id='+self.file.id

class ContentListStyle:
    def __init__(self, name, label, icon, template):
        self.name = name
        self.label = label
        self.icon = icon
        self.template = template

    def getName(self):
        return self.name
    
    def getLabel(self):
        return self.label

    def getIcon(self):
        return self.icon

    def getTemplate(self):
        return self.template

liststyles=[ContentListStyle("list","Listen-Ansicht","list.png","frontend/content_list.html"),
            ContentListStyle("thumbnail","Thumbnail-Ansicht","thumb.png","frontend/content_thumb.html"),
            ContentListStyle("text","Text-Ansicht","text.png","frontend/content_text.html"),
           ]
           #ContentListStyle("dummystyle","dummystyle","","")

def getListStyle(name):
    if name!="default":
        for style in liststyles:
            if style.getName()==name:
                return style
    return liststyles[0]

class ContentList(Content):
    def __init__(self,files,collection=None,words=None):
        self.nr = -1
        self.page = 0
        self.words = words
        self.files = files
        self.num = len(files)
        self.collection = collection
        self.content = None
        self.id2pos = {}
        self.sortfield = self.collection.get("sortfield")
        if self.sortfield:
            self.files.sort(self.sortfield)
        liststylename = self.collection.get("style")
        if liststylename:
            self.liststyle = getListStyle(liststylename)
        else:
            self.liststyle = getListStyle("default")

    def length(self):
        return self.num
    
    def actual(self):
        return "(%d/%d)" % (int(self.nr)+1, self.num)

    def in_list(self,id):
        return id in self.id2pos
    
    def link_first(self):
        self.id2pos[self.files[0].id] = 0
        return "/node?id=" + self.files[0].id
    def link_last(self):
        self.id2pos[self.files[self.num-1].id] = self.num-1
        return "/node?id=" + self.files[self.num-1].id

    def link_prev(self):
        if self.nr>0:
            self.id2pos[self.files[self.nr-1].id] = self.nr-1
            return "/node?id=" + self.files[self.nr-1].id
        else:
            return self.link_first()
    def link_next(self):
        if self.nr<self.num-1:
            self.id2pos[self.files[self.nr+1].id] = self.nr+1
            return "/node?id=" + self.files[self.nr+1].id
        else:
            return self.link_last()
    def link_back(self):
        return "node?back=y"
    
    def feedback(self,req):
        myid = req.params.get("id")
        if myid:
            self.nr = self.id2pos[myid]

        if "page" in req.params:
            self.page = int(req.params.get("page"))
            self.nr = -1
       
        if "back" in req.params:
            self.nr = -1

        if "sortfield" in req.params:
            self.sortfield = req.params["sortfield"]
            self.files.sort(self.sortfield)

        if self.nr>=0 and self.nr<self.num:
            self.content = ContentNode(self.files[self.nr],self.nr,self.num,self.words)
        else:
            self.content = None
        
        # style selection
        if "style" in req.params:
            newstyle = req.params.get("style")
            print "Overloading style display for collection",self.collection.id,"(set to",newstyle,")"
            req.session["liststyle-"+self.collection.id] = getListStyle(newstyle)

        if self.content:
            return self.content.feedback(req)
    
    def getSortFields(self):
        sortfields = []
        if len(self.files):
            for field in self.files[0].getType().getMetaFields():
                if "o" in field.getOption():
                    sortfields.append(field)
        return sortfields


    def html(self,req):
        if self.content:
            headline = athana.getTAL("web/frontend/content_nav.html", {"nav": self}, macro="navheadline", language=lang(req))
            return headline + self.content.html(req)

        nav_list = list()
        nav_page = list()

        files_per_page = 9

        min = 0
        max = (len(self.files)+files_per_page-1)/files_per_page-1
        left = self.page - 6
        right = self.page + 6
        if left < 0:
            left = 0
        if right > max or right >= max-2:
            right = max
        if left <= min+2:
            left = min

        if left > min:
            nav_list.append("/node?page="+str(min))
            nav_list.append('...')
            nav_page.append(min)
            nav_page.append(-1)

        for a in range(left, right+1):
            nav_list.append("/node?page="+str(a))
            nav_page.append(a)
        
        if right < max:
            nav_list.append('...')
            nav_list.append("/node?page="+str(max))
            nav_page.append(-1)
            nav_page.append(max)

        tal_files = []

        i = 0
        for i in range(self.page*files_per_page,(self.page+1)*files_per_page):
            if i < self.num:
                file = self.files[i]
                self.id2pos[self.files[i].id] = i
                tal_files += [SingleFile(file,i,self.num)]
            i = i + 1

        liststyle = req.session.get("liststyle-"+self.collection.id, "") # user/session setting for liststyle?
        if not liststyle:
            # no, use collection default
            liststyle = self.liststyle
            print "Use default style",self.liststyle

        filesHTML = req.getTAL("web/frontend/content_nav.html", {
                 "nav_list":nav_list, "nav_page":nav_page, "act_page":self.page, 
                 "sortfield":self.sortfield, "sortfields":self.getSortFields(),
                 "files":tal_files, "maxresult":len(self.files), "op":""}, macro="files")

        contentList = req.getTAL(liststyle.getTemplate(), {
                "nav_list":nav_list, "nav_page":nav_page, "act_page":self.page, 
                 "files":tal_files, "maxresult":len(self.files), "op":""})
        return filesHTML + '<div id="nodes">'+contentList + '</div><div id="page_nav">' + filesHTML + '</div>'
       
    
#paths
def getPaths(node, access):
    list = []
    def r(node, path, collections):
        #if node.type == "collection":
        if node in tree.getRoot("collections").getChildren():
            collections[node.id] = node
        if node is tree.getRoot():
            return
        for p in node.getParents():
            path.append(p)
            if p is tree.getRoot("collections"):
                path2 = []
            else:
                path2 = path
            r(p, path2, collections)
        return path
        
    paths = []
    
    collections = {}
    p = r(node, [], collections)
    if p:
        for node in p:
            if access.hasReadAccess(node):
                if node.type in ("directory", "home"):
                    paths.append(node)
                if node is tree.getRoot("collections") or node.type=="root":
                    paths.reverse()
                    if len(paths)>1:
                        list.append(paths[1:])
                    paths =[]
    if len(list)>0:
        return list
    else:
        return []


class ContentNode(Content):
    def __init__(self,node,nr=0,num=0,words=None):
        self.node = node
        self.id = node.id
        self.paths = []
        self.nr = nr
        self.num = num
        self.words = words
        self.collection = getCollection(node)
        collections={}
       
    def actual(self):
        return "(%d/%d)" % (int(self.nr)+1, self.num)
    def html(self,req):
        paths = ""
        if not self.node.can_open():
            plist = getPaths(self.node, AccessData(req))
            paths = athana.getTAL("web/frontend/content_nav.html", {"paths": plist}, macro="paths", language=lang(req))
        return self.node.show_node_big(req) + paths

def fileIsNotEmpty(file):
    f = open(file)
    s = f.read().strip()
    f.close()
    if s: return 1
    else: return 0
        
def mkContentNode(req): 
    access = AccessData(req)
    id = req.params["id"]
    try:
        node = tree.getNode(id)
    except tree.NoSuchNodeError:
        return ContentError("No such node")
    if not access.hasReadAccess(node):
        return ContentError("Permission denied")

    if node.type in ["directory","collection"]:
        if "files" not in req.params:
            for f in node.getFiles():
                if f.type == "content" and f.mimetype == "text/html" and os.path.isfile(f.getPath()) and fileIsNotEmpty(f.getPath()):
                    return ContentNode(node)
        access = AccessData(req)
        ids = []
        nodes = access.filter(node.getAllChildren())
        for c in nodes:
            if c.type != "directory":
                ids += [c.id]
        c = ContentList(tree.NodeList(ids),getCollection(node))
        c.node = node
        return c
    else:
        return ContentNode(node)



class ContentError(Content):
    def __init__(self,error):
        self.error = error

    def html(self,req):
        return athana.getTAL("web/frontend/content_error.html", {"error":self.error}, language=lang(req))

class ContentArea(Content):
    def __init__(self):
        self.content = ContentNode(tree.getRoot("collections"))
        self.collection = None
        self.collectionlogo = None
    
    def getPath(self):
        path = []
        if hasattr(self.content,"node"):
            cd = self.content.node
            if cd != None:
                path.append(Link('', cd.getLabel(), ''))   
                while 1:
                    parents = cd.getParents()
                    if(len(parents)==0):
                        break
                    cd = parents[0]
                    if cd is tree.getRoot("collections") or cd is tree.getRoot():
                        break
                    path.append(Link('/?id='+cd.id+'&dir='+cd.id, cd.getLabel(), cd.getLabel())) 
        elif hasattr(self.content,"linkname") and hasattr(self.content,"linktarget"):
            path.append(Link(self.content.linktarget,self.content.linkname,self.content.linkname))
        path.reverse()
        return path

    def feedback(self,req):
        if "id" in req.params and not (hasattr(self.content,"in_list") and self.content.in_list(req.params["id"])):
            self.content = mkContentNode(req)
        elif req.params.get("searchmode","") == "simple" and req.params.get("submittype","") != "change":
            self.content = simple_search(req)
        elif req.params.get("searchmode","") == "extended" and req.params.get("submittype","") != "change":
            # extended search
            self.content = extended_search(req)
        else:
            newcontent = self.content.feedback(req)
            if newcontent:
                self.content = newcontent
        if hasattr(self.content,"collection"):
            self.collection = self.content.collection
            if self.collection:
                self.collectionlogo = CollectionLogo(self.collection)

    def actNode(self):
        try:
            if self.content.nr>=0 and len(self.content.files)>=self.content.nr:
                ntype = self.content.files[self.content.nr]
            else:
                ntype = self.content.node
            return ntype
        except:
            return None
        
    def html(self,req):
        styles = []
        if hasattr(self.content,"in_list") and not self.content.content:
            styles = liststyles
        if "raw" in req.params:
            path = ""
        else:
            path = req.getTAL("web/frontend/content_nav.html", {"path": self.getPath(), "styles":styles, "logo":self.collectionlogo}, macro="path")
        return path + '\n<!-- CONTENT START -->\n<div id="nodes">' +  self.content.html(req) + '</div>\n<!-- CONTENT END -->\n'

class CollectionLogo(Content):
    def __init__(self,collection):
        self.collection = collection
        self.path = None
        for f in self.collection.getFiles():
            if f.getType()=="image":
                self.path = '/file/'+str(self.collection.id)+'/'+f.getName()

    def getPath(self):
        return self.path

    def getURL(self):
        return self.collection.get("url")

    def getShowOnHTML(self):
        return self.collection.get("showonhtml")
        

def getContentArea(req):
    if len(req.params):
        try:
            c = req.session["contentarea"]
        except KeyError:
            c = req.session["contentarea"] = ContentArea()
        return c
    else:
        c = req.session["contentarea"] = ContentArea()
        return c

