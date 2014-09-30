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

import os
import logging
import core.users as users
import core.acl as acl
import core.tree as tree
import core.config as config
import utils.date as date
import utils.urn as urn
import utils.hash as hashid
import utils.mail as mail
import utils.doi as doi
import utils.pathutils as pathutils
from core.translation import lang, t


def getContent(req, ids):
    """
    The standard method,  which has to be implemented by every module.
    It's called in edit.py, where all the modules will be identified.
    """
    user = users.getUserFromRequest(req)
    access = acl.AccessData(req)
    node = tree.getNode(ids[0])
    access_nobody = 'nicht Jeder'

    # first prove if the user has the required rights to call this module
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
         'urn_type': req.params.get('urn_type'),
         'host': config.get('host.name'),
         'creator': users.getUser(node.get('creator'))
         }

    if user.isAdmin():
        if 'id_type' in req.params:
            if req.params.get('id_type') == 'hash':
                createHash(node)
            if req.params.get('id_type') == 'urn':
                createUrn(node, req.params.get('namespace'), req.params.get('urn_type'))
            if req.params.get('id_type') == 'doi':
                try:
                    createDOI(node)
                except:
                    return req.error(500, "doi was not successfully registered")

            if any(identifier in node.attributes for identifier in ('hash', 'urn', 'doi')):
                if not node.get('system.identifierdate'):
                    node.set('system.identifierdate', date.now())
                if node.get('system.identifierstate') != '2':
                    node.set('system.identifierstate', '2')

                    # add nobody rule if not set
                    if node.getAccess('write') is None:
                        node.setAccess('write', access_nobody)
                    else:
                        if access_nobody not in node.getAccess('write'):
                            node.setAccess('write', ','.join([node.getAccess('write'), access_nobody]))

                try:
                    mailtext = req.getTAL('web/edit/modules/identifier.html', v, macro='generate_identifier_usr_mail_2')
                    mail.sendmail(config.get('email.admin'),
                                  users.getUser(node.get('creator')).get('email'),
                                  'Vergabe eines Idektifikators / Generation of an Identifier',
                                  mailtext)

                except mail.SocketError:
                    logging.getLogger('backend').error('failed to send Autorenvertrag mail to user %s' % node.get('creator'))
                    v['msg'] = t(lang(req), 'edit_identifier_mail_fail')

        if node.get('system.identifierstate') != '2':
            v['msg'] = t(lang(req), 'edit_identifier_state_0_1_admin')
        else:
            v['msg'] = t(lang(req), 'edit_identifier_state_2_admin')

    else:
        if pathutils.isDescendantOf(node, tree.getRoot('collections')):
            if not node.get('system.identifierstate'):
                if 'id_type' in req.params:
                    try:
                        # fetch autorenvertrag
                        attachment = []
                        autorenvertrag_name = 'formular_autorenvertrag.pdf'
                        autorenvertrag_path = os.path.join(config.get('paths.tempdir'),
                                                           autorenvertrag_name)

                        if not os.path.isfile(autorenvertrag_path):
                            logging.getLogger('backend').error(
                                "Unable to attach Autorenvergrag. Attachment file not found: '%s'" % autorenvertrag_path)
                            raise IOError('Autorenvertrag was not located on disk at %s. Please send this error message to %s' %
                                          (autorenvertrag_path, config.get('email.admin')))
                        else:
                            attachment.append((autorenvertrag_path, 'Autorenvertrag.pdf'))

                        # notify user
                        mailtext_user = req.getTAL(
                            'web/edit/modules/identifier.html', v, macro='generate_identifier_usr_mail_1_' + lang(req))
                        mail.sendmail(config.get('email.admin'),
                                      user.get('email'),
                                      t(lang(req), 'edit_identifier_mail_title_usr_1'),
                                      mailtext_user,
                                      attachments_paths_and_filenames=attachment)

                        # notify admin
                        mailtext_admin = req.getTAL('web/edit/modules/identifier.html', v, macro='generate_identifier_admin_mail')
                        mail.sendmail(config.get('email.admin'),
                                      config.get('email.admin'),
                                      'Antrag auf Vergabe eines Identifikators',
                                      mailtext_admin)

                        node.set('system.identifierstate', '1')

                        # add nobody rule
                        print node.getAccess('write')
                        if node.getAccess('write') is None:
                            node.setAccess('write', access_nobody)
                        else:
                            if access_nobody not in node.getAccess('write'):
                                node.setAccess('write', ','.join([node.getAccess('write'), access_nobody]))

                    except mail.SocketError:
                        logging.getLogger('backend').error('failed to send identifier request mail')
                        v['msg'] = t(lang(req), 'edit_identifier_mail_fail')
                else:
                    v['msg'] = t(lang(req), 'edit_identifier_state_0_usr')

            if node.get('system.identifierstate') == '1':
                v['show_form'] = False
                v['msg'] = t(lang(req), 'edit_identifier_state_1_usr')
        else:
            v['show_form'] = False
            v['msg'] = t(lang(req), 'edit_identifier_state_published')

    v['hash_val'] = node.get('hash')
    v['urn_val'] = node.get('urn')
    v['doi_val'] = node.get('doi')

    # hides form if all identifier types are already set
    if all(idents != '' for idents in (v['hash_val'], v['urn_val'], v['doi_val'])):
        v['show_form'] = False
        v['msg'] = t(lang(req), 'edit_identifier_all_types_set')

    return req.getTAL('web/edit/modules/identifier.html', v, macro='set_identifier')


def createUrn(node, namespace, urn_type):
    """
    @param node for which the URN should be created
    @param namespace of the urn; list of the namespaces can be found here: http://www.iana.org/assignments/urn-namespaces/urn-namespaces.xml
    @param urn_type e.q. diss, epub, etc
    """
    if node.get('urn') and (node.get('urn').strip() != ''):  # keep the existing urn, if there is one
        logging.getLogger('everything').info('urn already exists for node %s' % node.id)
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
    if node.get('hash') and (node.get('hash').strip() != ''):  # if a hash-id already exists for this node, do nothing
        logging.getLogger('everything').info('hash already exists for node %s' % node.id)
    else:
        node.set('hash', hashid.getChecksum(node.id))


def createDOI(node):
    """
    @param node for which the doi should be created
    """
    if node.get('doi') and (node.get('doi').strip() != ''):
        logging.getLogger('everything').info('doi already exists for node %s' % node.id)
    else:
        node.set('doi', doi.generate_doi_live(node))
        meta_file = doi.create_meta_file(node)
        doi_file = doi.create_doi_file(node)
        meta_response, meta_content = doi.post_file('metadata', meta_file)
        doi_response, doi_content = doi.post_file('doi', doi_file)

        if any(response != 201 for response in (meta_response, doi_response)):
            node.removeAttribute('doi')
            os.remove(meta_file)
            os.remove(doi_file)
            logging.getLogger('backend').error('doi was not successfully registered, META: %s %s | DOI: %s %s' %
                                               (meta_response, meta_content, doi_response, doi_content))
            raise Exception('doi was not successfully registered, META: %s %s | DOI: %s %s' %
                            (meta_response, meta_content, doi_response, doi_content))
