# -*- coding: utf-8 -*-

# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import functools as _functools
import json
import os.path
import logging
import re
import datetime

from mediatumtal import tal

from core import request_handler as _request_handler
import core.translation as _core_translation
import core.users as users
import core.config as _core_config

from core.metatype import Metatype
from utils.fileutils import importFile
import utils.fileutils as _utils_fileutils
from utils.utils import suppress
from core import Node
from core import db

q = db.query

logg = logging.getLogger(__name__)


def mkfilelist(targetnode, files, deletebutton=0, language=None, request=None, macro="m_upload_filelist"):
    if request:
        return tal.processTAL(
                dict(
                    files=files,
                    node=targetnode,
                    delbutton=deletebutton,
                   ),
                file="metadata/upload.html",
                macro=macro,
                request=request,
               )
    else:
        return tal.getTAL(
                "metadata/upload.html",
                dict(
                    files=files,
                    node=targetnode,
                    delbutton=deletebutton,
                   ),
                macro=macro,
                language=language,
               )


def getFilelist(node, fieldname=None):

    fs = node.files
    # filter files for this fieldname, or for all fields
    pattern = "metafield-upload.{}".format(fieldname or "")

    filelist = []

    for f in fs:
        f_type = f.filetype
        if f_type.startswith(pattern):
            f_retrieve = f.abspath
            try:
                f_mtime = unicode(datetime.datetime.utcfromtimestamp(os.path.getmtime(f_retrieve)))
            except:
                logg.exception("exception in getFilelist, formatting datestr failed, using fake date")
                f_mtime = "2099-01-01 12:00:00.00 " + f.base_name
            _t = (f_mtime, f.base_name, f.mimetype, f.size, f_type, f_retrieve, f)
            filelist.append(_t)

    filelist.sort()

    filelist2 = [_t[-1] for _t in filelist]

    return filelist, filelist2


class m_upload(Metatype):

    name = "upload"

    def getEditorHTML(self, field, value="", width=40, lock=0, language=None, required=None):
        try:
            fieldname = field.name
        except:
            fieldname = None

        try:
            warning = self.translation_labels[language]['upload_notarget_warning']
        except:
            logg.exception("exception in getEditorHTML, using default language")
            warning = self.translation_labels[_core_config.languages[0]]['upload_notarget_warning']

        context = dict(
            lock=lock,
            value=value,
            width=width,
            name=field.getName(),
            field=field,
            language=language,
            warning=warning,
            system_lock=1 if lock else 0,
            required=1 if required else None,
        )

        with suppress(Exception, warn=False):
            if field.get("system.lock"):
                context['system_lock'] = 1

        s = tal.getTAL(
                "metadata/upload.html",
                context,
                macro="editorfield",
                language=language,
               )
        if field.getName():
            s = s.replace("____FIELDNAME____", "%s" % field.getName())
        elif fieldname:
            s = s.replace("____FIELDNAME____", "%s" % fieldname)
        else:
            logg.warning("metadata: m_upload: no fieldname found")
        return s

    def getFormattedValue(self, metafield, maskitem, mask, node, language, html=True):
        fieldname = metafield.getName()
        value = node.get(metafield.getName())

        filelist, filelist2 = getFilelist(node, fieldname)

        if mask:
            masktype = mask.get('masktype')
            if masktype in ['shortview', 'export']:
                pass
            else:
                html_filelist = mkfilelist(
                    node, filelist2, deletebutton=0, language=language, request=None, macro="m_upload_filelist_nodebig")
                html_filelist = html_filelist.replace("____FIELDNAME____", "%s" % fieldname)
                value = html_filelist
        else:
            html_filelist = mkfilelist(node, filelist2, deletebutton=0, language=language, request=None, macro="m_upload_filelist")
            html_filelist = html_filelist.replace("____FIELDNAME____", "%s" % fieldname)
            value = html_filelist

        return (metafield.getLabel(), value)


    translation_labels = dict(
        de=dict(
            upload_popup_title="MDT-m_upload",
            fieldtype_upload="MDT-m_upload Feld",
            fieldtype_upload_desc="Feld MDT-m_upload",
            upload_titlepopupbutton=u"MDT-m_upload öffnen",
            upload_done=u"Übernehmen",
            upload_filelist_loc="Link",
            upload_filelist_size=u"Grösse",
            upload_filelist_type="Typ",
            upload_filelist_mimetype="Mimetype",
            upload_filelist_delete_title=u"Datei löschen und zurück zum Upload",
            upload_filelist_open_title=u"Datei öffnen",
            upload_notarget_warning="WARNUNG: Upload ist erst mit Zielknoten aktiv.",
        ),
        en=dict(
            upload_popup_title="MDT-m_upload",
            fieldtype_upload="MDT-m_upload field",
            fieldtype_upload_desc="field for MDT-m_upload",
            upload_titlepopupbutton="open MDT-m_upload",
            upload_done="Done",
            upload_filelist_loc="Link",
            upload_filelist_size="Size",
            upload_filelist_type="Type",
            upload_filelist_mimetype="Mimetype",
            upload_filelist_delete_title="Delete File and back to Upload",
            upload_filelist_open_title="Open File",
            upload_notarget_warning="WARNING: upload will only be active with a targetnode",
        ),
    )


def handle_request(req):

    user = users.user_from_session()
    
    if not user.is_admin:
        # XXX: this handler is unsafe for use by non-admins. 
        # We temporarily disable it for use in the editor. 
        # This means that the upload metadatatype cannot be used anymore.
        return 404
    
    errors = []

    if "cmd" in req.params:
        cmd = req.params["cmd"]
        if cmd == "list_files":

            targetnodeid = req.params.get("targetnodeid", "")
            m_upload_field_name = req.params.get("m_upload_field_name", "")

            n = q(Node).get(targetnodeid)

            s = {'response': 'response for cmd="%s"' % cmd}

            if not n.has_read_access():
                msg = "m_upload: no access for user '%s' to node %s ('%s', '%s') from '%s'" % (
                    user.login_name, n.id, n.name, n.type, ustr(req.remote_addr))
                logg.info("%s", msg)

                errors.append(msg)
                s['errors'] = errors
                req.response.set_data(req.params.get("jsoncallback") + "(%s)" % json.dumps(s, indent=4))
                req.response.status_code = 403
                return 403

            filelist, filelist2 = getFilelist(n, m_upload_field_name)
            filelist = [_t[0:-1] for _t in filelist]

            s['filelist'] = filelist

            html_filelist = mkfilelist(n, filelist2, deletebutton=1, language=None, request=req)
            html_filelist = html_filelist.replace("____FIELDNAME____", "%s" % m_upload_field_name)

            s['html_filelist'] = html_filelist

            req.response.set_data(req.params.get("jsoncallback") + "(%s)" % json.dumps(s, indent=4))
            req.response.status_code = 200

            return 200

        elif cmd == 'delete_file':

            s = {'response': 'response for cmd="%s"' % cmd}

            f_name = req.params.get('prefixed_filename', '')
            f_name = f_name[len('delete_'):]

            targetnodeid = req.params.get("targetnodeid", "")
            m_upload_field_name = req.params.get("m_upload_field_name", "")

            n = q(Node).get(targetnodeid)
            fs = n.files

            if not n.has_data_access():
                msg = "m_upload: no access for user '%s' to node %s ('%s', '%s') from '%s'" % (
                    user.login_name, n.id, n.name, n.type, ustr(req.remote_addr))
                logg.info("%s", msg)
                errors.append(msg)

                s['errors'] = errors
                req.response.set_data(req.params.get("jsoncallback") + "(%s)" % json.dumps(s, indent=4))
                req.response.status_code = 403
                return 403

            for f in fs:
                if f.getName() == f_name:
                    logg.info("metadata m_upload: going to remove file '%s' from node '%s' (%s) for request from user '%s' (%s)",
                        f_name, n.name, n.id, user.login_name, req.remote_addr)
                    filepath = f.abspath
                    filecount = len(getFilelist(n, m_upload_field_name)[0])
                    n.files.remove(f)
                    n.set(m_upload_field_name, filecount - 1)
                    try:
                        os.remove(filepath)
                    except Exception, e:
                        msg = "metadata m_upload: could not remove file %r from disk for node %r for request from '%s': %s" % (filepath, n, ustr(req.remote_addr), str(e))
                        errors.append(msg)
                        logg.exception("%s", msg)
                    break

            db.session.commit()

            s['errors'] = errors
            req.response.set_data(req.params.get("jsoncallback") + "(%s)" % json.dumps(s, indent=4))
            req.response.status_code = 200
            return 200
        else:
            s = {'response': 'response for cmd="%s" not completely implemented feature' % cmd}
            req.response.set_data(req.params.get("jsoncallback") + "(%s)" % json.dumps(s, indent=4))
            return 200

    s = {}

    if "submitter" in req.params.keys():

        submitter = req.params.get("submitter", "").split(';')[0]

        targetnodeid = req.params.get("targetnodeid_FOR_" + submitter, None)
        targetnode = None
        if targetnodeid:
            targetnode = q(Node).get(targetnodeid)
            if targetnode is None:
                msg = "metadata m_upload: targetnodeid='%s' for non-existant node for upload from '%s'" % (ustr(targetnodeid), ustr(req.remote_addr))
                errors.append(msg)
                logg.error("%s", msg)
        else:
            msg = "metadata m_upload could not find 'targetnodeid' for upload from '%s'" % ustr(req.remote_addr)
            errors.append(msg)
            logg.error("%s", msg)

        if targetnode and not targetnode.has_data_access():
            msg = "m_upload: no access for user '%s' to node %s ('%s', '%s') from '%s'" % (
                user.login_name, ustr(targetnode.id), targetnode.name, targetnode.type, ustr(req.remote_addr))
            logg.error("%s", msg)
            errors.append(msg)

            s['errors'] = errors
            req.response.set_data("%s" % json.dumps(s, indent=4))
            return

        filename = None
        file_key = "m_upload_file_FOR_" + submitter

        if file_key in req.files:

            file = req.files[file_key]
            req.params.pop(file_key, None)

            filename = file.filename

        else:
            msg = _core_translation.t(
                    _core_translation.set_language(req.accept_languages),
                    "no file for this field submitted",
                )
            errors.append(msg)

        if filename:
            nodeFile = importFile(
                _utils_fileutils.sanitize_filename(filename),
                file,
                filetype='metafield-upload.{}'.format(submitter)
               )

            if not nodeFile:
                msg = "metadata m_upload: could not create file node for request from '%s'" % (ustr(req.remote_addr))
                errors.append(msg)
                logg.error("%s", msg)

        if targetnode and filename:
            filecount = len(getFilelist(targetnode, submitter)[0])
            targetnode.files.append(nodeFile)
            targetnode.set(submitter, filecount + 1)
            db.session.commit()

            copy_report = "uploaded file: {}".format(filename)

        else:
            copy_report = ""

    else:
        msg = "metadata m_upload: could not find submitter for request from '%s'" % (ustr(req.remote_addr))
        errors.append(msg)
        logg.error("%s", msg)

    s = {
        'errors': errors,
        'copy_report': copy_report,
    }

    req.response.set_data("%s" % json.dumps(s, indent=4))
    req.response.status_code = 200

    return 200
