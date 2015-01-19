"""
 mediatum - a multimedia content repository

 Copyright (C) 2007 Arne Seifert <seiferta@in.tum.de>
 Copyright (C) 2007 Matthias Kramm <kramm@in.tum.de>
 Copyright (C) 2014 Werner F. Neudenberger <werner.neudenberger@tum.de>

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
import sys

from core.transition import httpstatus
import core.users as users

from web.frontend.frame import getNavigationFrame

from pprint import pformat as pf

aclasses = {}

logg = logging.getLogger(__name__)

DEBUG = True

USE_EXAMPLES = True


def get_orderpos2name_list():
    return sorted([(aclasses[name].orderpos, name) for name in aclasses])


def get_default_orderpos():
    """return maximal orderpos +1 or 1 if dictionary is empty"""
    if not aclasses:
        return 1
    return max([aclasses[name].orderpos for name in aclasses]) + 1


def register_aclass(name, inst, force=False):
    if name in aclasses and not force:
        raise ValueError("name '%s' exists already" % name)
        return
    if not hasattr(inst, "orderpos"):
        inst.orderpos = get_default_orderpos()
    aclasses[name] = inst
    logg.debug("registers %r, now %r entries registered" % (name, len(aclasses)))


class HTMLSnippet:

    def __init__(self, name="unnamed", atype=None, orderpos=None, template=""):
        self.name = name
        self.atype = atype
        self.orderpos = orderpos if orderpos else get_default_orderpos()
        self.template = template

    def setUserDetails(self, user, detail_dict, req=None, **kwargs):
        targetnode = users.getHomeDir(user)
        for key in detail_dict:
            target_key = "system.%s.%s" % (self.name, key)
            target_value = ustr(detail_dict[key])
            targetnode.set(target_key, target_value)
            logg.debug("setting user detail: %r = %r", target_key, target_value)

    def getUserDetails(self, user, req=None, **kwargs):
        targetnode = users.getHomeDir(user)
        res = dict(targetnode.items())
        if logg.isEnabledFor(logging.DEBUG):
            _d = pf(res)
            logg.debug("retrieving user details: %s", _d)
        return res

    def getHTML(self, user, req=None, **kwargs):
        return self.template

    def getJSON(self, user, req=None, **kwargs):
        return ""

    def getFormat(self, user, format="html", req=None, **kwargs):
        return getHTML(self, user, req=None, **kwargs)

    def allowUser(self, user, req=None, **kwargs):
        return False

    def callback(self, req=None, **kwargs):
        return ""


def show_user_data(req):
    error = ""

    # XXX: dead code?
    if USE_EXAMPLES and 'examples' in req.params:
        try:
            import userdata_examples
            reload(userdata_examples)
        except:
            logg.exception("Error loading examples")

    if "jsonrequest" in req.params:
        python_callback_key = req.params.get("python_callback_key", "")
        if python_callback_key and python_callback_key in aclasses:
            req.write(aclasses[python_callback_key].callback(req=req))
        return

    user = users.getUserFromRequest(req)
    user_homedir = {}
    if not user.isGuest():
        user_homedir = users.getHomeDir(user)

    navframe = getNavigationFrame(req)
    navframe.feedback(req)

    udclasses = sorted([(uc.orderpos, uc) for uc in aclasses.values()])
    udclasses = [t[1] for t in udclasses]

    ctx = {
        "error": error,
        "user": user,
        "user_homedir": user_homedir,
        "pf": pf,
        "udclasses": udclasses,
        "req": req,
    }

    navframe.write(req, req.getTAL("web/frontend/userdata.html", ctx, macro="show_user_data"))

    return httpstatus.HTTP_OK
