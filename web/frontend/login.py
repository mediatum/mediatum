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
import users
import athana
import config
import tree
import logging
from frontend.frame import getNavigationFrame
from translation import *

#
# login form
#
def display_login(req, error=None):
    navframe = getNavigationFrame(req)
    navframe.feedback(req)

    user = users.getUserFromRequest(req)
   
    v = {"error":error, "user":user}
    contentHTML = req.getTAL("login.html", v, macro="login")
    navframe.write(req, contentHTML)
    return athana.HTTP_OK

#
# display form for password change
#
def display_changepwd(req, error=None):
    navframe = getNavigationFrame(req)
    navframe.feedback(req)
    
    user = users.getUserFromRequest(req)

    v = {"error":error, "user":user}
    contentHTML = req.getTAL("login.html", v, macro="change_pwd")
    navframe.write(req, contentHTML)
    return athana.HTTP_OK

#
# validate login
#
def login_submit(req):
    user = req.params.get("user",config.get("user.guestuser"))
    password = req.params.get("password","")

    masterpassword = config.get("user.masterpassword")

    if users.checkLogin(user, password)==1 or (masterpassword and password==masterpassword):
        user = users.getUser(user)
        req.session["user"] = user
        logging.getLogger('usertracing').info(user.name + " logged in")

        if user.stdPassword():
            return display_changepwd(req,3);    
        else:        
            req.request["Location"] = req.makeLink("node", {"id":tree.getRoot("collections").id})
            return athana.HTTP_MOVED_TEMPORARILY;
    else:
        return display_login(req, "login_error")

#
# logout current user
#
def logout(req):
    try:
        del req.session["user"]
    except:
        pass
    req.request["Location"] = req.makeLink("node", {"id":tree.getRoot("collections").id})
    return athana.HTTP_MOVED_TEMPORARILY;

#
# password change evaluation
#
def changepwd_submit(req):
    user = users.getUserFromRequest(req)

    if user.getName() == config.get("user.guestuser"):
        req.request["Location"] = req.makeLink("node", {"id":tree.getRoot("collections").id})
        return athana.HTTP_MOVED_TEMPORARILY;
    
    else:
        if users.checkLogin(user.getName(), req.params["password_old"])==0:
            return display_changepwd(req, 1) # old wrong
        
        elif req.params["password_new1"] != req.params["password_new2"]:
            return display_changepwd(req, 2) # no match
        
        else:
            user.setPassword(req.params["password_new2"])
            req.request["Location"] = req.makeLink("node", {"id":tree.getRoot("collections").id})
            return athana.HTTP_MOVED_TEMPORARILY;

