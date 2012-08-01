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
import core.acl as acl
import core.tree as tree
import core.config as config
import utils.date as date
import utils.urn as urn
import utils.hash as hashid


def getContent(req, ids):
    """
    The standard method, which has to be implemented by every module.
    It's called in edit.py, where all the modules will be identified.
    """
    user = users.getUserFromRequest(req)
    access = acl.AccessData(req)
    node = tree.getNode(ids[0])
    
    # first proof, if the user has the required rights to call this module
    if "sortfiles" in users.getHideMenusForUser(user) or not access.hasWriteAccess(node):
        return req.getTAL("web/edit/edit.html", {}, macro="access_error")
    
    v = {'msg':'',
         'urn_institutionid': config.get('urn.institutionid'),
         'urn_pubtypes': config.get('urn.pubtypes').split(";"),
         'namespaces': config.get('urn.namespace').split(";")
         }
    
    # check what type of identifier should be created
    if 'id_type' in req.params:
        if req.params.get('id_type') == 'hash':
            createHash(node)
            v['msg'] = 'HashID: ' + node.get('hash')
        if req.params.get('id_type') == 'urn':
            createUrn(node, req.params.get('namespace'), req.params.get('urn_type'))
            v['msg'] = 'URN: ' + node.get('urn')
            
    return req.getTAL("web/edit/modules/identifier.html", v, macro="set_identifier")


def createUrn(node, namespace, urn_type):
    """
    @param node for which the URN should be created
    @param namespace of the urn; list of the namespaces can be found here: http://www.iana.org/assignments/urn-namespaces/urn-namespaces.xml
    @param urn_type e.q. diss, epub, etc
    """
    if node.get("urn") and (node.get("urn").strip() != ""): # keep the existing urn, if there is one
        pass
    else: 
        try:
            d = date.parse_date(node.get("date-accepted"))
        except:
            d = date.now()
        niss = '%s-%s-%s-0' %(urn_type, date.format_date(d, '%Y%m%d'), node.id)
        node.set("urn", urn.buildNBN(namespace, config.get('urn.institutionid'), niss))


def createHash(node):
    """
    @param node for which the hash-id should be created
    """
    if node.get("hash") and (node.get("hash").strip() != ""): # if a hash-id allready exists for this node, do nothing
        pass
    else:
        node.set( "hash", hashid.getChecksum(node.id) )


