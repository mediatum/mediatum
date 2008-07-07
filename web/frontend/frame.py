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
import sys
import traceback
import core.users as users
import core.config as config
import time
import core.athana as athana
import os
import core.search.query

from utils.dicts import SortedDict
from schema.schema import getMetadataType
from web.frontend.browsingtree import browsingtree
from utils.dicts import SortedDict
from utils.utils import getCollection, Link, iso2utf8, isCollection
from core.acl import AccessData,getRootAccess
from core.translation import translate, lang, t
from core.metatype import Context

class Portlet:
    def __init__(self):
        self.folded = 0
        self.name = "common"
        self.user = users.getUser(config.get("user.guestuser", ""))
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
        self.user = users.getUserFromRequest(req)
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

def getSearchMask(collection):
    print "getSearchMask(",collection.id
    if collection.get("searchtype") == "none":
        return None
    mask = None
    n = collection
    if collection.get("searchtype") == "parent":
        while len(n.getParents()):
            if n.get("searchtype") == "own":
                break
            n = n.getParents()[0]
    if n.get("searchtype") == "own":
        try:
            mask = tree.getRoot("searchmasks").getChild(n.get("searchmaskname"))
        except tree.NoSuchNodeError:
            mask = None
    return mask

class Searchlet(Portlet):

    def __init__(self, collection):
        Portlet.__init__(self)
        self.name = "searchlet"
        self.extended = 0
        self.folded = 0
        self.collection = collection
        self.searchmask = getSearchMask(collection)

        self.values = [None,"","",""]
        self.req = None
        self.initialize()

    def insideCollection(self):
        return self.collection and self.collection.id != tree.getRoot("collections").id

    def initialize(self):
        types = {}
        firsttype=None

        # get searchfields for collection
        self.searchfields = SortedDict()

        if self.searchmask:
            for field in self.searchmask.getChildren().sort():
                self.searchfields[field.id] = field.name
        self.names = [None,None,None,None]

    def feedback(self, req):
        Portlet.feedback(self,req)
        self.req = req
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
            if name == "full" or not name:
                f = None
            else:
                f = tree.getNode(name).getFirstField()

            if "query"+str(i) in req.params or "query"+str(i)+"-from" in req.params:
                if f and f.getFieldtype()=="date":
                    self.values[i] = req.params.get("query"+str(i)+"-from","") + ";" +  req.params.get("query"+str(i)+"-to","")
                else:
                    self.values[i] = req.params.get("query"+str(i),"")

        if "query" in req.params:
            self.values[0] = req.params["query"]

    def hasExtendedSearch(self):
        return self.searchmask is not None

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
        if self.names[i] and self.names[i]!="full":
            f = tree.getNode(self.names[i]).getFirstField()
        g = None
        if f is None: # All Metadata
            # quick&dirty
            f = g = getMetadataType("text")
        return f.getSearchHTML(Context(g,value=self.values[i], width=width, name="query"+str(i), language=lang(self.req), collection=self.req.params.get('collection'), user=users.getUserFromRequest(self.req), ip=self.req.ip))

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
            if isCollection(tree.getNode(req.params["fold"])):
                self.dirinreq = False

        if "unfold" in req.params:
            self.browse_unfold_link = "&unfold="+req.params["unfold"]
            if isCollection(tree.getNode(req.params["unfold"])):
                self.dirinreq = True

    def canOpen(self):
        return self.collection.id != tree.getRoot("collections").id
    def getFrameLink(self):
        return '/treeframe?id='+self.collection.id+'&'+'currentdir='+self.currentdir.id+self.browse_fold_link+self.browse_unfold_link

    def buildBrowsingTree(self, req):
        self.browsingtree = browsingtree(req)

    def getBrowsingTree(self):
        return self.browsingtree

    def DirOpen(self):
        return self.dirinreq
    
class NavTreeEntry:
    def __init__(self, col, node, indent):
        self.col = col
        self.node = node
        self.id = node.id
        self.indent = indent
        self.defaultopen = indent==0
        self.hassubdir = 0
        self.folded = 1
        self.active = 0
        for c in self.node.getChildren():
            if c.type == "directory":
                self.hassubdir = 1
                self.folded = 1
                break

    def isRoot(self):
        return self.node.type=='collections'
    def getFoldLink(self):
        return "?cfold="+self.node.id+"&dir="+self.node.id+"&id="+self.node.id
    def getUnfoldLink(self):
        return "?cunfold="+self.node.id+"&dir="+self.node.id+"&id="+self.node.id
    def isFolded(self):
        return self.folded
    def getStyle(self):
        return "padding-left: %dpx" % (self.indent*6)
    def getText(self):
        return self.node.getLabel()
    def getClass(self):
        if self.indent > 1:
            return "lv1"
        else:
            return "lv0"

# NOTE: the whole collection/browsing tree stuff is horriby complex, and
# should be rewritten from scratch

def isParentOf(node, parent):
    parents = node.getParents()
    print [n.name for n in parents]
    if node == parent:
        return 1
    if parent in parents:
        return 1
    for p in parents:
        if isParentOf(p, parent):
            return 1
    return 0

class Collectionlet(Portlet):
    def __init__(self):
        Portlet.__init__(self)
        self.name="collectionlet"
        self.collection = tree.getRoot("collections")
        self.folded = 0
        self.m = {}
        self.col_data = None
        self.hassubdir = 0
    
        def f(m,node,indent):
            m[node.id] = NavTreeEntry(self, node,indent)
            for c in node.getChildren():
                if isCollection(c):
                    f(m, c, indent+1)
        f(self.m, tree.getRoot("collections"), 0)

    def getCurrent(self):
        return self.collection

    def feedback(self,req):
        Portlet.feedback(self,req)
        if "dir" in req.params:
            dirid = req.params["dir"]
            try:
                dir = tree.getNode(dirid)
                if self.collection.type=="collections" or not isParentOf(dir, self.collection):
                    self.collection = getCollection(dir)
            except tree.NoSuchNodeError:
                pass

        if "id" in req.params:
            id = req.params["id"]
            try:
                node = tree.getNode(id)
                if self.collection.type=="collections" or not isParentOf(node, self.collection):
                    self.collection = getCollection(node)
            except tree.NoSuchNodeError:
                pass

        access = AccessData(req)

        for c in self.m.values():
            if not c.defaultopen:
                c.folded = 1
            c.active = 0

        if "cunfold" in req.params:
            id = req.params["cunfold"]
            if id in self.m:
                self.m[id].folded = 0
        
        if self.collection.id in self.m:
            self.m[self.collection.id].folded = 0
            self.m[self.collection.id].active = 1

        parents = [self.collection]
        while parents:
            p = parents.pop()
            if p.id in self.m:
                self.m[p.id].folded = 0
            parents += p.getParents()

        col_data = []
        def f(col_data,node,indent):
            if not access.hasReadAccess(node):
                return
            if not node.id in self.m:
                # some new node FIX-ME we should rebuild the tree
                return
               
            data = self.m[node.id]

            col_data += [data]

            if not data.folded or data.defaultopen:
                for c in node.getChildren().sort():
                    if isCollection(c):
                        f(col_data,c, indent+1)
        f(col_data,tree.getRoot("collections"),0)
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
        self.params["act_node"] = req.params.get("id", req.params.get("dir", ""))
        return req.writeTAL("web/frontend/frame.html", self.params)


def getNavigationFrame(req):
    try:
        c = req.session["navframe"]
    except KeyError:
        c = req.session["navframe"] = NavigationFrame()
    return c


