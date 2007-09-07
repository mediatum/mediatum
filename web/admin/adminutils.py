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

from utils.utils import Link
from core.translation import t, lang

def getAdminStdVars(req):
    if req.params.get("page","")=="0":
        page = "?page=0"
    else:
        page = ""
    return {"user": users.getUserFromRequest(req), "page":page, "op":req.params.get("op","")}

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

        # self.page = 0 or None -> all entries
        self.page = int(req.params.get("page",1))
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
        

    def getStart(self):
        return int(self.start)
       
    def getEnd(self):
        return int(self.end)
      
    def getNoPages(self):
        return int(math.ceil(float(len(self.list))/float(config.settings["admin.pageitems"])))

    def printPageList(self):
        order = self.req.params.get("order","")
        detail=""
        try:
            detail = "&detailof=" + self.req.params["detailof"]
        except:
            None

        try:
            detail = "&maskof=" + self.req.params["maskof"]
        except:
            None

        if order!="":
            detail +="&order="+order

        ret = ""
        if self.page>0:
            p = 1
            ret = '['
            while p<=self.getNoPages():
                if p==self.page:
                    ret += ' <a class="actpage" href="/admin/'+self.path+'?page='+str(p)+detail+'" title="'+t(self.language,"admin_page")+' '+str(p)+'">'+str(p)+'</a> '
                else:
                    ret += ' <a href="/admin/'+self.path+'?page='+str(p)+detail+'" title="'+t(self.language,"admin_page")+' '+str(p)+'">'+str(p)+'</a> '
                p += 1
            ret += "] "
        return ret


    def printPageAll(self):
        try:
            link = "?detailof=" + self.req.params["detailof"] + "&order=" + self.req.params.get("order","")
        except:
            link = "?order=" + self.req.params.get("order","")
            
        try:
            link += "&maskof="+self.req.params["maskof"]
        except:
            None

        if self.page!=0:
            return '<a href="/admin/'+self.path+link+'&page=0" title="'+t(self.language,"admin_allelements_title")+'">'+t(self.language,"admin_allelements")+'</a>'
        else:
            return '<a href="/admin/'+self.path+link+'" title="'+t(self.language,"admin_pageelements_title")+'">'+t(self.language,"admin_pageelements")+'</a>'

    def OrderColHeader(self, cols, order="", addparams=""):
        order = self.req.params.get("order","")
        ordercol=0
        orderdir=0
        retList = []

        if order != "":
            ordercol = int(order[0:1])
            orderdir = int(order[1:])
        i=0
        ret = ""
        for col in cols:
            if col!="":
                if i==ordercol:
                    if orderdir == 0:
                        retList += [Link("?page="+str(self.page)+ addparams + "&order=" +str(i)+"1", t(self.language,"admin_sort_label"), col+' <img src="/img/az.png" border="0" />')]
                    else:
                        retList += [Link("?page="+str(self.page)+ addparams + "&order=" +str(i)+"0", t(self.language,"admin_sort_label"), col+' <img src="/img/za.png" border="0" />')]
                else:
                    retList += [Link("?page="+str(self.page)+ addparams + "&order=" +str(i)+"0", t(self.language,"admin_sort_label"), col)]
            i+=1
        return retList

""" load module for admin area """
mymodules = {}
def findmodule(type):
    global mymodules
    if type in mymodules:
        return mymodules[type]
        
    print mymodules

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
        print op
        module = findmodule(op.split("_")[0])

        try:
            if op.index("_")>-1:
                return module.spc(req, op)
        except:
            return module.validate(req, op)


class Menu:
    def __init__(self, name):
        self.name = name
        self.item = list()

    def getName(self):
        return self.name

    def addItem(self, link):
        self.item.append((self.name+"_"+str(len(self.item)+1), link))
    def getItemList(self):
        return self.item


def adminNavigation():
    menu = list()
    submenu = Menu("admin_menu_1")
    submenu.addItem("/admin/usergroup")
    submenu.addItem("/admin/user")
    menu.append(submenu)

    submenu = Menu("admin_menu_2")
    submenu.addItem("/admin/acls")
    menu.append(submenu)

    submenu = Menu("admin_menu_3")
    submenu.addItem("/admin/metatype")
    menu.append(submenu)

    submenu = Menu("admin_menu_4")
    submenu.addItem("/admin/workflow")
    menu.append(submenu)

    submenu = Menu("admin_menu_5")
    submenu.addItem("/admin/logfile")
    menu.append(submenu)

    return menu
