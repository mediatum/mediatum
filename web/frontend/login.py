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
import core.users as users
import web.admin.modules.user as usermodule

import core.athana as athana
import core.config as config
import core.tree as tree

import logging
import random, md5

import utils.mail as mail
import utils.date as date

from web.frontend.frame import getNavigationFrame
from core.translation import lang, t

def display_login(req, error=None):
    if "LoginReset" in req.params.keys():
        del req.params['error']

    if len(req.params)>0 and not "error" in req.params.keys():
        # user changed from login to browsing
        p = ""
        for key in req.params:
            p += "&"+str(key)+"="+req.params.get(key) 
        req.request["Location"] = "http://"+config.get("host.name")+"/node?"+p[1:];
        return athana.HTTP_MOVED_TEMPORARILY
        
    navframe = getNavigationFrame(req)
    navframe.feedback(req)

    user = users.getUserFromRequest(req)
   
    v = {"error":error, "user":user}
    contentHTML = req.getTAL("web/frontend/login.html", v, macro="login")
    navframe.write(req, contentHTML)
    return athana.HTTP_OK

def display_changepwd(req, error=None):
    navframe = getNavigationFrame(req)
    navframe.feedback(req)
    
    user = users.getUserFromRequest(req)

    v = {"error":error, "user":user}
    contentHTML = req.getTAL("web/frontend/login.html", v, macro="change_pwd")
    navframe.write(req, contentHTML)
    return athana.HTTP_OK

def login_submit(req):
    user = req.params.get("user",config.get("user.guestuser"))
    password = req.params.get("password","")

    masterpassword = config.get("user.masterpassword")
    user = users.checkLogin(user, password)

    if user or (masterpassword and password==masterpassword):
        req.session["user"] = user
        logging.getLogger('usertracing').info(user.name + " logged in")
        
        if user.getUserType()!="":
            x = users.getExternalAuthentificator(user.getUserType())           
            if x.stdPassword(user):
                return display_changepwd(req,3)
        else:
            if user.stdPassword():
                return display_changepwd(req,3)
       
        if config.get("config.ssh", "") == "yes":
            req.request["Location"] = "https://"+config.get("host.name")+"/node?id="+tree.getRoot("collections").id;
        else:
            req.request["Location"] = "/node?id="+tree.getRoot("collections").id;
        return athana.HTTP_MOVED_TEMPORARILY
    else:
        req.params['error']  = "1"
        return display_login(req, "login_error")

def logout(req):
    try:
        del req.session["user"]
    except:
        pass
    req.request["Location"] = req.makeLink("node", {"id":tree.getRoot("collections").id})
    return athana.HTTP_MOVED_TEMPORARILY;

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
        
def display_pwdforgotten(req, error=None):
    navframe = getNavigationFrame(req)
    navframe.feedback(req)

    user = users.getUserFromRequest(req)
    
    v = {"error":error, "user":user}

    contentHTML = req.getTAL("web/frontend/login.html", v, macro="pwdforgotten")
    navframe.write(req, contentHTML)
    return athana.HTTP_OK

# def mkKey() taken from /workflow/workflow.py
def mkKey():
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    s = ""
    for i in range(0,16):
        s += alphabet[random.randrange(0,len(alphabet)-1)]
    return s

def pwdforgotten_submit(req):
    if req.params.get("change_language"):
        return display_login(req)

    username = req.params.get("user", "")
    email = req.params.get("email", "")
    
    if username == '':
        error = "pwdforgotten_noentry"
        req.params['error'] = error
        return display_pwdforgotten(req, error)
    
    if username:
        
        targetuser = users.getUser(username)
        
        if not targetuser:
            logging.getLogger('usertracing').info("new password requested for non-existing user: "+username)
            error="pwdforgotten_nosuchuser"
            req.params['error'] = error
            return display_pwdforgotten(req, error)
        
        else:
            targetemail = targetuser.getEmail()
            
            password = users.makeRandomPassword()
            randomkey=mkKey()

            targetuser.set("newpassword.password", md5.md5(password).hexdigest())
            targetuser.set("newpassword.time_requested", date.format_date())
            targetuser.set("newpassword.activation_key", randomkey)
            targetuser.set("newpassword.request_ip", req.ip)
            
            v = {}
            v["name"] = targetuser.getName()
            v["host"] = config.get("host.name")
            v["login"] = targetuser.getName()
            v["language"] = lang(req)
            v["activationlink"] = v["host"]+"/pwdforgotten_activate?key=%s-%s" % (targetuser.id, randomkey)
            
            text = req.getTAL("web/frontend/login.html", v, macro="emailtext").strip()
            text = text.replace("[$newpassword]", password)
            
            v = {}
            v["email"] = targetuser.getEmail()
            v["userid"] = targetuser.getName()
            
            navframe = getNavigationFrame(req)
            navframe.feedback(req)
            
            # going to send the mail
            text = text.replace("[wird eingesetzt]", password)
            
            try:
                mail.sendmail(config.get("email.admin"),targetemail,t(lang(req),"pwdforgotten_email_subject"),text)
                logging.getLogger('usertracing').info("new password requested for user: %s - activation email sent" % username)
            except mail.SocketError:
                print "Socket error while sending mail"
                logging.getLogger('usertracing').info("new password requested for user: %s - failed to send activation email" % username)
                return req.getTAL("web/frontend/login.html", v, macro="sendmailerror")
            
            contentHTML = req.getTAL("web/frontend/login.html", v, macro="pwdforgotten_butmailnowsent")
            navframe.write(req, contentHTML)
            return athana.HTTP_OK
    
def pwdforgotten_activate(req):
    navframe = getNavigationFrame(req)
    navframe.feedback(req)
    
    if req.params.get("change_language"):
        return display_login(req)
    
    id, key = req.params.get("key").replace("/", "").split('-')
    targetuser = users.getUser(id)
    
    if targetuser.get("newpassword.activation_key")==key:
        newpassword = targetuser.get("newpassword.password")
        
        if newpassword:
            targetuser.set("password", newpassword)
            print "password reset for user '%s' (id=%s) reset" % (targetuser.getName(), targetuser.id)
            targetuser.set("newpassword.password", "")
            targetuser.set("newpassword.time_activated", date.format_date())
            
            username=targetuser.getName()
            requested=targetuser.get("newpassword.time_requested")
            ip=targetuser.get("newpassword.request_ip")
            
            logging.getLogger('usertracing').info("new password activated for user: %s - was requested: %s by %s" % (username, requested, ip))
            
            v={"username": targetuser.getName()}
            
            contentHTML = req.getTAL("web/frontend/login.html", v, macro="pwdforgotten_password_activated")
            navframe.write(req, contentHTML)
            return athana.HTTP_OK
        
        else:
            print "invalid key: wrong key or already used key"
            v = {}
            contentHTML = req.getTAL("web/frontend/login.html", v, macro="pwdforgotten_password_invalid_key")
            navframe.write(req, contentHTML)
            return athana.HTTP_OK
            

