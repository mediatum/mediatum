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
from utils.log import logException

from utils.dicts import SortedDict
from schema.schema import getMetadataType
from utils.dicts import SortedDict
from utils.utils import getCollection, getDirectory, Link, iso2utf8, isCollection, isDirectory, isParentOf
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
        try:
            f = None
            if self.names[i] and self.names[i]!="full":
                f = tree.getNode(self.names[i]).getFirstField()
            g = None
            if f is None: # All Metadata
                # quick&dirty
                f = g = getMetadataType("text")
            return f.getSearchHTML(Context(g,value=self.values[i], width=width, name="query"+str(i), 
                                   language=lang(self.req), collection=self.collection, 
                                   user=users.getUserFromRequest(self.req), ip=self.req.ip))
        except:
            # workaround for unknown error
            logException("error during getSearchField(i)")
            return ""

class NavTreeEntry:
    def __init__(self, col, node, indent, small=0):
        self.col = col
        self.node = node
        self.id = node.id
        self.indent = indent
        self.defaultopen = indent==0
        self.hassubdir = 0
        self.folded = 1
        self.active = 0
        self.small = small
        for c in self.node.getChildren():
            if isCollection(c) or isDirectory(c):
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
    def getText(self,accessdata):
        try:
            if self.node.type == "directory":
                count = 0
                for n_t,num in self.node.getAllOccurences(accessdata).items():
                    if n_t.getContentType() != "directory":
                        count += num
                if count==0:
                    return self.node.getLabel()
                else:
                    return self.node.getLabel()+" (" + str(count) + ")"
            else:
                return self.node.getLabel()
        except:
            logException("error during NavTreeEntry.getText()")
            return "Node (0)"
    def getClass(self):
        if self.node.type == "directory":
            return "lv2"
        else:
            if self.indent > 1:
                return "lv1"
            else:
                return "lv0"

class RecursionException:
    pass

class Collectionlet(Portlet):
    def __init__(self):
        Portlet.__init__(self)
        self.name="collectionlet"
        self.collection = tree.getRoot("collections")
        self.directory = self.collection
        self.folded = 0
        self.col_data = None
        self.hassubdir = 0
        self.hide_empty = False
    
    def getCurrent(self):
        return self.collection

    def feedback(self,req):
        Portlet.feedback(self,req)
        if "dir" in req.params or "id" in req.params:
            id = req.params.get("id", req.params.get("dir"))
            try:
                node = tree.getNode(id)
                if isCollection(node):
                    self.collection = node
                    self.directory = node
                else:
                    if isDirectory(node):
                        self.directory = node
                    else: 
                        if not isDirectory(self.directory) or not isParentOf(node, self.directory):
                            self.directory = getDirectory(node)
                    if self.collection.type=="collections" or not isParentOf(node, self.collection):
                        self.collection = getCollection(node)
            except tree.NoSuchNodeError:
                pass
      
        try:
            self.hide_empty = self.collection.get("style_hide_empty") == "1"
        except:
            self.hide_empty = False

        access = AccessData(req)
        
        # open all parents, so we see that node
        opened = {}
        parents = [self.directory]
        counter=0
        while parents:
            counter=counter+1
            if counter>15:
                raise RecursionException
            p = parents.pop()
            opened[p.id] = 1
            parents += p.getParents()
      
        m = {}
        def f(m,node,indent,hide_empty):
            if indent>15:
                raise RecursionException
            if not access.hasReadAccess(node):
                return

            children = None
            if hide_empty:
                ok = 0
                for type,num in node.getAllOccurences(access).items():
                    if not isDirectory(type) and not isCollection(type) and num:
                        ok = 1
                if not ok:
                    return

            m[node.id] = e = NavTreeEntry(self, node, indent, node.type=="directory")
            if node.id in opened or e.defaultopen:
                m[node.id].folded = 0
                if children is None:
                    children = node.getChildren()
                for c in children:
                    if isCollection(c) or isDirectory(c):
                        if c.get("style_hide_empty") == "1":
                            hide_empty=1
                        f(m, c, indent+1, hide_empty)

        f(m, tree.getRoot("collections"), 0, self.hide_empty)

        if "cunfold" in req.params:
            id = req.params["cunfold"]
            if id in m:
                m[id].folded = 0
        
        if self.directory.id in m:
            m[self.directory.id].folded = 0
            m[self.directory.id].active = 1
        
        if self.collection.id in m:
            m[self.collection.id].active = 1

        col_data = []
        def f(col_data,node,indent):
            if indent>15:
                raise RecursionException
            if not node.id in m:
                return
               
            data = m[node.id]

            col_data += [data]

            if not data.folded or data.defaultopen:
                for c in node.getChildren().sort():
                    if isCollection(c) or isDirectory(c):
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
    def getSearch(self,collection):
        if collection.id not in self.searchmap:
            self.searchmap[collection.id] = Searchlet(collection)
        return self.searchmap[collection.id]

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

        #<ul class="nav_depth03" tal:condition="python:browse.collection.id==data.id and not data.isFolded() and data.hassubdir">
        self.params = {"user": user, "userlinks": userlinks, "t":t, "navigation":navigation, "language":front_lang}
        
    def write(self, req, contentHTML, show_navbar=1):
        self.params["content"] = contentHTML
        self.params["show_navbar"] = show_navbar
        self.params["act_node"] = req.params.get("id", req.params.get("dir", ""))
        self.params["acl"] = AccessData(req)
        return req.writeTAL("web/frontend/frame.html", self.params)


def getNavigationFrame(req):
    try:
        c = req.session["navframe"]
    except KeyError:
        c = req.session["navframe"] = NavigationFrame()
    return c
