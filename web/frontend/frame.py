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
import tree
import sys
import traceback
import users
import config
import time
import athana
import os
from SortedDict import SortedDict
from objtypes.metadatatype import getMetadataType

from frontend.browsingtree import browsingtree, cleartree
from translation import *


import search.query

from SortedDict import *
from utils import getCollection, Link, iso2utf8
from acl import AccessData
from translation import translate, lang

class Portlet:
    def __init__(self):
        self.folded = 0
        self.name = "common"
    def isFolded(self):
        return self.folded
    def close(self):
        if self.canClose():
            self.folded = 1
    def open(self):
        if self.canOpen():
            self.folded = 0
    def canClose(self):
        return 1
    def canOpen(self):
        return 1
    def feedback(self,req):
        r = req.params.get(self.name,"")
        if r == "unfold":
            self.open()
        elif r == "fold":
            self.close()
        self.language = lang(req)
    def getFoldUnfoldLink(self):
        if self.folded:
            return "node?"+self.name+"=unfold"
        else:
            return "node?"+self.name+"=fold"

class Searchlet(Portlet):

    def __init__(self, collection):
        Portlet.__init__(self)
        self.name = "searchlet"
        self.extended = 0
        self.folded = 0
        self.collection = collection
        self.datatype = None
        self.values = [None,"","",""]
        self.initialize()

    def insideCollection(self):
        return self.collection and self.collection.id != tree.getRoot("collections").id

    def initialize(self):
        types = {}
        firsttype=None

        # get searchfields for collection
        self.searchfields = SortedDict()
        datatypes = []
        for mtype,num in self.collection.getAllOccurences().items():
            if num>0:
                if mtype.name not in ("directory", "collection"):
                    datatypes += [mtype]

        self.datatype = None
        for mtype in datatypes:
            self.datatype = mtype
            for field in self.datatype.getSearchFields():
                self.searchfields[field.name] = field.getLabel()
            if len(self.searchfields):
                break
        
        self.names = [None,None,None,None]

    def feedback(self, req):
        Portlet.feedback(self,req)
        if "searchmode" in req.params:
            if req.params["searchmode"] == "simple":
                self.extended = 0
            if req.params["searchmode"] == "extended":
                self.extended = 1

        for i in [1,2,3]:
            if "field"+str(i) in req.params:
                newname = req.params.get("field"+str(i),"full")
                if newname != self.names[i]:
                    self.values[i] = ""
                self.names[i] = newname
            name = self.names[i]
            f = None
            if self.datatype:
                f = self.datatype.getMetaField(name)
            if "query"+str(i) in req.params or "query"+str(i)+"-from" in req.params:
                if f and f.getFieldtype()=="date":
                    self.values[i] = req.params.get("query"+str(i)+"-from","") + ";" +  req.params.get("query"+str(i)+"-to","")
                else:
                    self.values[i] = req.params.get("query"+str(i),"")

        if "query" in req.params:
            self.values[0] = req.params["query"]

    def hasExtendedSearch(self):
        if self.collection.get("no_extsearch")=="1":
            return False
        return self.collection.type in ("collection","directory") and self.collection.get("searchstyle") != "simple"

    def isSimple(self):
        return not self.extended
    def isExtended(self):
        return self.extended

    def query(self):
        return self.values[0]
    def searchLinkSimple(self):
        return "node?searchmode=simple&submittype=change"
    def searchLinkExtended(self):
        return "node?searchmode=extended&submittype=change"
    def searchActiveLeft(self):
        return not self.extended
    def searchActiveRight(self):
        return self.extended
    def getSearchFields(self):
        return self.searchfields
    def getSearchField(self, i, width=174):
        f = None
        if self.datatype and str(self.names[i])!="None":
            f = self.datatype.getMetaField(self.names[i])
        if f is None: # All Metadata
            # quick&dirty
            f = getMetadataType("text")
            return f.getSearchHTML(f,self.values[i], width, "query"+str(i), language=self.language)
        return f.getSearchHTML(self.values[i], width, "query"+str(i), language=self.language)

class Browselet(Portlet):
    def __init__(self, collection):
        Portlet.__init__(self)
        self.name = "browselet"
        self.collection = collection
        self.currentdir = collection
        self.browse_fold_link = ""
        self.browse_unfold_link = ""
        self.folded = 0
        self.dirinreq = False
        if collection.type == "collections":
            self.folded = 1
    def feedback(self,req):
        Portlet.feedback(self,req)
        if "dir" in req.params:
            dirid = req.params["dir"]
            try:
                self.currentdir = tree.getNode(dirid)
            except tree.NoSuchNodeError:
                pass
        else:
            req.params["dir"] = self.currentdir.id

        self.browse_fold_link = ""
        self.browse_unfold_link = ""
        if "fold" in req.params:
            self.browse_fold_link = "&fold="+req.params["fold"]
            if tree.getNode(req.params["fold"]) in tree.getRoot("collections").getChildren():
                self.dirinreq = False

        if "unfold" in req.params:
            self.browse_unfold_link = "&unfold="+req.params["unfold"]
            if tree.getNode(req.params["unfold"]) in tree.getRoot("collections").getChildren():
                self.dirinreq = True

    def canOpen(self):
        return self.collection.id != tree.getRoot("collections").id
    def getFrameLink(self):
        return '/treeframe?id='+self.collection.id+'&'+'currentdir='+self.currentdir.id+self.browse_fold_link+self.browse_unfold_link

    def buildBrowsingTree(self, req):
        cleartree()
        self.browsingtree = browsingtree(req)

    def getBrowsingTree(self):
        return self.browsingtree

    def DirOpen(self):
        return self.dirinreq
    	

class Collectionlet(Portlet):
    def __init__(self):
        Portlet.__init__(self)
        self.name="collectionlet"
        self.collection = tree.getRoot("collections")
        self.folded = 0
    def getCurrent(self):
        return self.collection
    def feedback(self,req):
        Portlet.feedback(self,req)
        if "dir" in req.params:
            dirid = req.params["dir"]
            try:
                dir = tree.getNode(dirid)
                if dir in tree.getRoot("collections").getChildren():
                    self.collection = dir
            except tree.NoSuchNodeError:
                pass
        elif "id" in req.params:
            id = req.params["id"]
            try:
                node = tree.getNode(id)
                self.collection = getCollection(node)
            except tree.NoSuchNodeError:
                pass

        col_data = []
        col_data = [tree.getRoot("collections")] + list(AccessData(req).filter(tree.getRoot("collections").getChildren().sort()))
        self.col_data = col_data

    def getCollections(self):
        return self.col_data

    def getCollUnfold(id):
        if self.req.params.get("colunfold","")==str(id):
            return True
        else:
            return False
        
class Navlet(Portlet):
    def __init__(self):
        Portlet.__init__(self)
        self.name="navlet"
        self.collection = tree.getRoot("collections")
        self.folded = 0
    
    def feedback(self,req):
        ni_data = []
        ni_data = list(AccessData(req).filter(tree.getRoot("navigation").getChildren().sort()))
        self.ni_data = ni_data
    
class Pathlet:
    def __init__(self,currentdir):
        self.currentdir = currentdir
    def getPath(self):
        #path
        path = []
        if type(self.currentdir) == type(""):
            path.append(Link(self.currentdir, self.currentdir, self.currentdir))
        else:
            cd = self.currentdir;
            if cd != None:
                path.append(Link('', cd.name, ''))
                while 1:
                    parents = cd.getParents()
                    if(len(parents)==0):
                        break
                    cd = parents[0]
                    if cd is tree.getRoot():
                        break
                    path.append(Link('/?id='+cd.id+'&dir='+cd.id, cd.name, cd.name))
        path.reverse()
        
class CollectionMapping:
    def __init__(self):
        self.searchmap = {}
        self.browsemap = {}
        self.collection_portlet = Collectionlet()
    def getSearch(self,collection):
        if collection.id not in self.searchmap:
            self.searchmap[collection.id] = Searchlet(collection)
        return self.searchmap[collection.id]
    def getBrowse(self,collection):
        if collection.id not in self.browsemap:
            self.browsemap[collection.id] = Browselet(collection)
        return self.browsemap[collection.id]


def getSessionSetting(req, name, default):
    try:
        value = req.params[name]
        value[0]
    except:
        pass
    try:
        value = req.session[name]
    except:
        value = default
        req.session[name] = default

    return value

class UserLinks:
    def __init__(self,user):
        self.user = user
        self.id = None
        self.language = ""
    def feedback(self,req):
        if "id" in req.params:
            self.id = req.params["id"]
        self.language = lang(req)
    def getLinks(self):
        l = [Link("/logout", t(self.language,"sub_header_logout_title"), t(self.language,"sub_header_logout"))]
        if config.get("user.guestuser")==self.user.getName():
            l = [Link("/login", t(self.language,"sub_header_login_title"), t(self.language,"sub_header_login"))]
        
        if self.user.isEditor():
            idstr=""
            if self.id:
                idstr = "?id="+self.id
            l += [Link("/edit/edit"+idstr, t(self.language,"sub_header_edit_title"), t(self.language,"sub_header_edit"))]
        
        if self.user.isAdmin():
            l += [Link("/admin", t(self.language,"sub_header_administration_title"), t(self.language,"sub_header_administration"))]
        
        if self.user.isWorkflowEditor():
            l += [Link("/publish/", t(self.language,"sub_header_workflow_title"), t(self.language,"sub_header_workflow"))]

        if config.get("user.guestuser")!=self.user.getName() and "c" in self.user.getOption():
            l += [Link("/display_changepwd", t(self.language,"sub_header_changepwd_title"), t(self.language,"sub_header_changepwd"), "_parent")]
        return l


class NavigationFrame:
    def __init__(self):
        self.cmap = CollectionMapping()
        self.collection_portlet = Collectionlet()
        self.nav_portlet = Navlet()

    def feedback(self,req):
        #self.cmap.feedback(req)
        user = users.getUserFromRequest(req)

        userlinks = UserLinks(user)
        userlinks.feedback(req)

        #if not user.isGuest():
        #    l += [Link("/user", "Pers&ouml;nliche Daten", "Pers&ouml;nliche Daten")]

        t = time.strftime("%d.%m.%Y %H:%M:%S")    

        #tabs
        navigation = {}
        
        # collection
        collection_portlet = self.collection_portlet
        collection_portlet.feedback(req)
        col_selected = collection_portlet.collection
        navigation["collection"] = collection_portlet
        
        # search
        search_portlet = self.cmap.getSearch(col_selected)
        search_portlet.feedback(req)
        navigation["search"] = search_portlet

        # languages
        front_lang = {}
        front_lang["name"] = config.get("i18n.languages").split(",")
        front_lang["actlang"] = lang(req)

        # navitems
        nav_portlet = self.nav_portlet
        nav_portlet.feedback(req)
        navigation["navitem"] = nav_portlet

        # browse
        browse_portlet = self.cmap.getBrowse(col_selected)
        req.params["collection"] = collection_portlet.collection.id
        browse_portlet.feedback(req)
        browse_portlet.buildBrowsingTree(req)
        navigation["browse"] = browse_portlet
        self.params = {"user": user, "userlinks": userlinks, "t":t, "navigation":navigation, "language":front_lang}
        
    def write(self, req, contentHTML, show_navbar=1):
        self.params["content"] = contentHTML
        self.params["show_navbar"] = show_navbar
        return req.writeTAL("frame.html", self.params)


def getNavigationFrame(req):
    try:
        c = req.session["navframe"]
    except KeyError:
        c = req.session["navframe"] = NavigationFrame()
    return c


