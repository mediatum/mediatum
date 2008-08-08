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
import core.config as config
import math
import core.users as users
import sys
import traceback

from utils.utils import Link, Menu
from core.translation import t, lang

def getAdminStdVars(req):

    if req.params.get("page","")=="0":
        page = "?page=0"
    else:
        page = ""
    user = users.getUserFromRequest(req)
    
    tabs = [("0-9", "09")]
    for i in range(65,91):
        tabs.append((unichr(i),unichr(i)))
    tabs.append(("admin_filter_else","-"))
    tabs.append(("admin_filter_all","*"))
    
    return {"user": user, "page":page, "op":req.params.get("op",""), "tabs":tabs, "actpage":req.params.get("page", req.params.get("actpage", "0"))}

def getOptionHeader(options):
    ret = '<table><tr>'
    for option in options:
        ret += '<td width="20px" align="center"><img src="/' + option.getImagesource()  + '" title="' + option.getName() + '"></td>'
    return [ret + '</tr></table>']

class Overview:
    def __init__(self, req, list):
        self.req = req
        self.path = req.path[1:]
        self.language = lang(req)
        self.stdVars = getAdminStdVars(self.req)

        # self.page = 0 or None -> all entries
        self.page = int(req.params.get("page",req.params.get("actpage",1)))
        if "firstpage" in req.params.keys():
            self.page = 1
        max_page = len(list)/int(config.settings["admin.pageitems"])
        if max_page+1<self.page:
            self.page = 1
            req.params["page"]=1

        if self.page==0:
            self.start = 0
            self.end = len(list)
        else:
            self.start = (self.page-1) * int(config.settings["admin.pageitems"])
            self.end = self.start + int(config.settings["admin.pageitems"])
        self.list = list
    
    def getStdVars(self):
        return self.stdVars
        
    def getStart(self):
        return int(self.start)
       
    def getEnd(self):
        return int(self.end)
      
    def getNoPages(self):
        return int(math.ceil(float(len(self.list))/float(config.settings["admin.pageitems"])))

    def printPageList(self):
        order = self.req.params.get("order","") 
        ret = ''
        if self.page>0:
            for p in range(1,self.getNoPages()+1):
                b_class = "admin_page"
                if p==self.page:
                    b_class = "admin_page_act"
                ret += '<button type="submit" name="page" class="'+b_class+'" title="'+t(self.language,"admin_page")+' '+str(p)+'" value="'+str(p)+'">'+str(p)+'</button> '
        if len(ret)==0:
            return ""
        return '[' + ret + '] '


    def printPageAll(self):
        if self.page!=0:
            return '<button name="resetpage" title="'+t(self.language,"admin_allelements_title")+'" class="admin_page" type="submit">'+t(self.language,"admin_allelements")+'</button>'
        else:
            return '<button name="firstpage" title="'+t(self.language,"admin_pageelements_title")+'" class="admin_page" type="submit">'+t(self.language,"admin_pageelements_title")+'</button>'

            
    def OrderColHeader(self, cols, order="", addparams=""):
        order = self.req.params.get("order","")
        ordercol=0
        orderdir=0
        retList = []

        if order != "":
            ordercol = int(order[0:1])
            orderdir = int(order[1:])
        i=0
        for col in cols:
            if col!="":
                if i==ordercol:
                    if orderdir == 0:
                        retList += [Link(str(i)+"1", t(self.language,"admin_sort_label"), col+' <img src="/img/az.png" border="0" />')]
                    else:
                        retList += [Link(str(i)+"0", t(self.language,"admin_sort_label"), col+' <img src="/img/za.png" border="0" />')]
                else:
                    retList += [Link(str(i)+"0", t(self.language,"admin_sort_label"), col)]
            i+=1
        return retList

""" evaluate current filter """
def getFilter(req):
    actfilter = req.params.get("actfilter", req.params.get("filter", "all")).lower()
    if "filterbutton" in req.params.keys():
        actfilter = req.params.get("filterbutton").lower()
    return actfilter

""" fills variable for sort column """
def getSortCol(req):
    order = req.params.get("order", "")
    for key in req.params.keys():
        if key.startswith("sortcol_"):
            order = key[8:]
            req.params["order"] = order
    return order

""" load module for admin area """
mymodules = {}
def findmodule(type):
    global mymodules
    if type in mymodules:
        return mymodules[type]

    try:
        m = __import__("web.admin.modules." + type)
        #m = eval("m.modules."+type)
        m = eval("m.admin.modules."+type)
    except:
        print "Warning: couldn't load module for type",type
        print sys.exc_info()[0], sys.exc_info()[1]
        traceback.print_tb(sys.exc_info()[2])
        import web.admin.modules.default
        m = __import__("web.admin.modules.default")
        m = eval("m.admin.modules.default")

    mymodules[type] = m
    return m

""" main method for content area """
def show_content(req, op):
    user = users.getUserFromRequest(req)

    if not user.inGroup("Administration"):
        return req.getTAL("web/admin/frame.html", {}, macro="errormessage")
    else:
        if op == "":
            op = "default"
        module = findmodule(op.split("_")[0])

        try:
            if op.index("_")>-1:
                return module.spc(req, op)
        except:
            return module.validate(req, op)



def adminNavigation():
    menu = list()
    try:
        submenu = Menu("admin_menu_0", "admin_menu_0_description","", "/admin")
        menu.append(submenu)
  
        submenu = Menu("admin_menu_1", "admin_menu_1_description", "/img/icons/usergroups.gif")
        submenu.addItem("/admin/usergroup","/img/icons/usergroups.gif")
        submenu.addItem("/admin/user", "/img/icons/users.gif")
        menu.append(submenu)

        submenu = Menu("admin_menu_2", "admin_menu_2_description", "/img/icons/groupperms.gif")
        submenu.addItem("/admin/acls")
        menu.append(submenu)

        submenu = Menu("admin_menu_3", "admin_menu_3_description", "/img/icons/datatypes.gif")
        submenu.addItem("/admin/metatype")
        submenu.addItem("/admin/mapping")
        menu.append(submenu)

        submenu = Menu("admin_menu_4", "admin_menu_4_description", "/img/icons/workflow.gif")
        submenu.addItem("/admin/workflows")
        menu.append(submenu)

        submenu = Menu("admin_menu_5", "admin_menu_5_description", "/img/icons/system.gif")
        submenu.addItem("/admin/logfile")
        submenu.addItem("/admin/flush")
        submenu.addItem("/admin/settings")
        menu.append(submenu)
        
        submenu = Menu("admin_menu_6", "admin_menu_6_description", "/img/icons/stat.gif")
        submenu.addItem("/admin/stats")
        menu.append(submenu)
        
        submenu = Menu("admin_menu_6", "", "", "../edit/")
        #menu.append(submenu)
        
        submenu = Menu("admin_menu_7", "", "/img/icons/viewsite.gif", "../")
        #menu.append(submenu)
        
        submenu = Menu("admin_menu_8", "", "/img/icons/logout.gif", "/logout")
        #menu.append(submenu)
        
    except TypeError:
        pass
    return menu
    
def getMenuItemID(menulist, path):
    if path=="":
        return ["admin_menu_0"]
    for item in menulist:
        for subitem in item.getItemList():
            if subitem[1].endswith(path):
                return [item.name,subitem[0]]
                
    return ["admin_menu_0"]


    
    
    
    
    