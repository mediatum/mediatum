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
import utils.mail as mail
from core.translation import lang, t


def getContent(req, ids):
    """
    The standard method,  which has to be implemented by every module.
    It's called in edit.py, where all the modules will be identified.
    """
    user = users.getUserFromRequest(req)
    access = acl.AccessData(req)
    node = tree.getNode(ids[0])

    # first proof, if the user has the required rights to call this module
    if 'sortfiles' in users.getHideMenusForUser(user) or not access.hasWriteAccess(node):
        return req.getTAL('web/edit/edit.html', {}, macro='access_error')

    if node.isContainer():
        nodes = ', '.join(node.getChildren().getIDs())
    else:
        nodes = node.get('node.id')

    v = {'msg': '',
         'urn_institutionid': config.get('urn.institutionid'),
         'urn_pubtypes': config.get('urn.pubtypes').split(';'),
         'namespaces': config.get('urn.namespace').split(';'),
         'user': user,
         'nodes': nodes,
         'type': req.params.get('id_type'),
         'show_form': True,
         'namespace': req.params.get('namespace'),
         'urn_type': req.params.get('urn_type')
    }

    if user.isAdmin():
        if 'id_type' in req.params:
            if req.params.get('id_type') == 'hash':
                createHash(node)
            if req.params.get('id_type') == 'urn':
                createUrn(node, req.params.get('namespace'), req.params.get('urn_type'))
            if req.params.get('id_type') == 'doi':
                createDOI(node, req.params.get('doi_input'))

            if any(identifier in node.attributes for identifier in ('hash', 'urn', 'doi')):
                if not node.get('system.identifierdate'):
                    node.set('system.identifierdate', date.now())
                if node.get('system.identifierstate') != '2':
                    node.set('system.identifierstate', '2')
                    #add nobody rule if not set
                    access_nobody = acl.getRule('nobody').getRuleStr()
                    if access_nobody not in node.getAccess('write'):
                        node.setAccess('write', ','.join([node.getAccess('write'), access_nobody]))

                try:
                    mailtext = req.getTAL('web/edit/modules/identifier.html', v, macro='generate_identifier_usr_mail')
                    mail.sendmail(config.get('email.admin'), user.get('email'),
                                  t(lang(req), 'edit_identifier_mail_title_complete'), mailtext)
                except mail.SocketError:
                    print 'Socket error while sending mail'
                    v['msg'] = t(lang(req), 'edit_identifier_mail_fail')

        if node.get('system.identifierstate') != '2':
            v['msg'] = t(lang(req), 'edit_identifier_state_0_1_admin')
        else:
            v['msg'] = t(lang(req), 'edit_identifier_state_2_admin')

    else:
        if not node.get('system.identifierstate'):
            if 'id_type' in req.params:
                try:
                    mailtext = req.getTAL('web/edit/modules/identifier.html', v, macro='generate_identifier_admin_mail')
                    mail.sendmail(config.get('email.admin'), config.get('email.admin'),
                                  t(lang(req), 'edit_identifier_mail_title'), mailtext)
                    node.set('system.identifierstate', '1')
                    #add nobody rule
                    access_nobody = node.getAccess('write') + ',' + acl.getRule('nobody').getRuleStr()
                    node.setAccess('write', access_nobody)

                except mail.SocketError:
                    print 'Socket error while sending mail'
                    v['msg'] = t(lang(req), 'edit_identifier_mail_fail')
            else:
                v['msg'] = t(lang(req), 'edit_identifier_state_0_usr')

        if node.get('system.identifierstate') == '1':
            v['show_form'] = False
            v['msg'] = t(lang(req), 'edit_identifier_state_1_usr')
        if node.get('system.identifierstate') == '2':
            v['show_form'] = False
            v['msg'] = t(lang(req), 'edit_identifier_state_2_usr')

    v['hash_val'] = node.get('hash')
    v['urn_val'] = node.get('urn')
    v['doi_val'] = node.get('doi')

    return req.getTAL('web/edit/modules/identifier.html', v, macro='set_identifier')


def createUrn(node, namespace, urn_type):
    """
    @param node for which the URN should be created
    @param namespace of the urn; list of the namespaces can be found here: http://www.iana.org/assignments/urn-namespaces/urn-namespaces.xml
    @param urn_type e.q. diss, epub, etc
    """
    if node.get('urn') and (node.get('urn').strip() != ''): # keep the existing urn, if there is one
        pass
    else:
        try:
            d = date.parse_date(node.get('date-accepted'))
        except:
            d = date.now()
        niss = '%s-%s-%s-0' % (urn_type, date.format_date(d, '%Y%m%d'), node.id)
        node.set('urn', urn.buildNBN(namespace, config.get('urn.institutionid'), niss))


def createHash(node):
    """
    @param node for which the hash-id should be created
    """
    if node.get('hash') and (node.get('hash').strip() != ''): # if a hash-id already exists for this node, do nothing
        pass
    else:
        node.set('hash', hashid.getChecksum(node.id))


def createDOI(node, doi):
    """
    @param node for which the doi should be created
    @param doi is the manually entered doi which should already have been created
    TODO: method needs to eventually create the DOI by itself instead of just accepting an already generated value
    """
    if node.get('doi') and (node.get('doi').strip() != ''):
        pass
    else:
        node.set('doi', doi)