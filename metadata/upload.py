# -*- coding: utf-8 -*-
"""
 mediatum - a multimedia content repository

 Copyright (C) 2011 Arne Seifert <arne.seifert@tum.de>
 Copyright (C) 2011 Werner F. Neudenberger <werner.neudenberger@mytum.de>

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

import json
import os.path
import logging
import re
import datetime

from mediatumtal import tal
from core.transition.athana_sep import athana_http as athana
import core.users as users

from core.metatype import Metatype
from core.translation import getDefaultLanguage, t, lang
from utils.fileutils import importFileToRealname
from core import Node
from core import db

q = db.query

logg = logging.getLogger(__name__)


def check_context():
    webcontexts = athana.contexts
    if (not filter(lambda x: x.name == '/md_upload', webcontexts)) and athana.GLOBAL_ROOT_DIR != "no-root-dir-set":
        logg.info('adding context md_upload')
        webcontext = athana.addContext("/md_upload", ".")
        webcontext_file = webcontext.addFile("metadata/upload.py")
        webcontext_file.addHandler("handle_request").addPattern("/.*")

check_context()


def mkfilelist(targetnode, files, deletebutton=0, language=None, request=None, macro="m_upload_filelist"):
    if request:
        return request.getTAL("metadata/upload.html", {"files": files, "node": targetnode, "delbutton": deletebutton}, macro=macro)
    else:
        return tal.getTAL(
            "metadata/upload.html", {"files": files, "node": targetnode, "delbutton": deletebutton}, macro=macro, language=language)


ALLOWED_CHARACTERS = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ' + '0123456789' + '+-_.'


def normalizeFilename(s, chars=ALLOWED_CHARACTERS):
    res = ''
    for c in s:
        if c in chars:
            res += c
        else:
            res += '_'
    return res


def getFilelist(node, fieldname=''):

    fs = node.files
    if fieldname:
        # get files for this fieldname only
        pattern = r'm_upload_%s_' % fieldname
    else:
        # get files for all m_upload fields
        pattern = r'm_upload_'

    filelist = []

    for f in fs:
        f_name = f.base_name
        if re.match(pattern, f_name):
            f_retrieve = f.abspath
            try:
                f_mtime = unicode(datetime.datetime.fromtimestamp(os.path.getmtime(f_retrieve)))
            except:
                logg.exception("exception in getFilelist, formatting datestr failed, using fake date")
                f_mtime = "2099-01-01 12:00:00.00 " + f_name
            _t = (f_mtime, f_name, f.mimetype, f.size, f.filetype, f_retrieve, f)
            filelist.append(_t)

    filelist.sort()

    filelist2 = [_t[-1] for _t in filelist]

    return filelist, filelist2


class m_upload(Metatype):

    disabled = "0"

    def getEditorHTML(self, field, value="", width=40, lock=0, language=None, required=None):
        check_context()

        try:
            fieldid = field.id
        except:
            fieldid = None

        try:
            fieldname = field.name
        except:
            fieldname = None

        try:
            warning = [t[1] for t in self.labels[language] if t[0] == 'upload_notarget_warning'][0]
        except:
            logg.exception("exception in getEditorHTML, using default language")
            warning = [t[1] for t in self.labels[getDefaultLanguage()] if t[0] == 'upload_notarget_warning'][0]

        context = {
            "lock": lock,
            "value": value,
            "width": width,
            "name": field.getName(),
            "field": field,
            "language": language,
            "warning": warning,
            "system_lock": 0,
            "required": self.is_required(required)
        }

        if lock:
            context['system_lock'] = 1

        try:
            if field.get("system.lock"):
                context['system_lock'] = 1
        except:
            pass

        s = tal.getTAL("metadata/upload.html", context, macro="editorfield", language=language)
        if field.getName():
            s = s.replace("____FIELDNAME____", "%s" % field.getName())
        elif fieldname:
            s = s.replace("____FIELDNAME____", "%s" % fieldname)
        else:
            logg.warn("metadata: m_upload: no fieldname found")
        return s

    def getFormattedValue(self, metafield, maskitem, mask, node, language, html=True):

        check_context()

        fieldname = metafield.getName()
        value = node.get(metafield.getName())

        filelist, filelist2 = getFilelist(node, fieldname)
        #filecount = len(filelist2)

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

    def getName(self):
        return "fieldtype_upload"

    def getInformation(self):
        return {"moduleversion": "1.0", "softwareversion": "1.1"}

    def getLabels(self):
        return m_upload.labels

    labels = {"de":

              [
                  ("upload_popup_title", "MDT-m_upload"),
                  ("fieldtype_upload", "MDT-m_upload Feld"),
                  ("fieldtype_text_desc", "Feld MDT-m_upload"),
                  ("upload_titlepopupbutton", u"MDT-m_upload öffnen"),
                  ("upload_done", u"Übernehmen"),
                  ("upload_filelist_loc", "Link"),
                  ("upload_filelist_size", u"Grösse"),
                  ("upload_filelist_type", "Typ"),
                  ("upload_filelist_mimetype", "Mimetype"),
                  ("upload_filelist_delete_title", u"Datei löschen und zurück zum Upload"),
                  ("upload_filelist_open_title", u"Datei öffnen"),
                  ("upload_notarget_warning", "WARNUNG: Upload ist erst mit Zielknoten aktiv."),
              ],
              "en":
              [
                  ("upload_popup_title", "MDT-m_upload"),
                  ("fieldtype_upload", "MDT-m_upload field"),
                  ("fieldtype_text_desc", "field for MDT-m_upload"),
                  ("upload_titlepopupbutton", "open MDT-m_upload"),
                  ("upload_done", "Done"),
                  ("upload_filelist_loc", "Link"),
                  ("upload_filelist_size", "Size"),
                  ("upload_filelist_type", "Type"),
                  ("upload_filelist_mimetype", "Mimetype"),
                  ("upload_filelist_delete_title", "Delete File and back to Upload"),
                  ("upload_filelist_open_title", "Open File"),
                  ("upload_notarget_warning", "WARNING: upload will only be active with a targetnode"),
              ]
              }


def handle_request(req):

    user = users.getUserFromRequest(req)
    errors = []

    if "cmd" in req.params:
        cmd = req.params["cmd"]
        if cmd == "list_files":

            targetnodeid = req.params.get("targetnodeid", "")
            m_upload_field_name = req.params.get("m_upload_field_name", "")

            n = q(Node).get(targetnodeid)

            s = {'response': 'response for cmd="%s"' % cmd}

            filelist, filelist2 = getFilelist(n, m_upload_field_name)
            filelist = [_t[0:-1] for _t in filelist]

            s['filelist'] = filelist

            html_filelist = mkfilelist(n, filelist2, deletebutton=1, language=None, request=req)
            html_filelist = html_filelist.replace("____FIELDNAME____", "%s" % m_upload_field_name)

            s['html_filelist'] = html_filelist

            req.write(req.params.get("jsoncallback") + "(%s)" % json.dumps(s, indent=4))

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
                    user.name, n.id, n.name, n.type, ustr(req.ip))
                logg.info(msg)
                errors.append(msg)

                s['errors'] = errors
                req.write(req.params.get("jsoncallback") + "(%s)" % json.dumps(s, indent=4))
                return 403

            for f in fs:
                if f.getName() == f_name:
                    logg.info("metadata m_upload: going to remove file '%s' from node '%s' (%s) for request from user '%s' (%s)",
                        f_name, n.name, n.id, user.name, req.ip)
                    n.removeFile(f)
                    try:
                        os.remove(f.retrieveFile())
                    except:
                        pass
                    break

            filecount = len(getFilelist(n, m_upload_field_name)[0])
            n.set(m_upload_field_name, filecount)

            s['errors'] = errors
            req.write(req.params.get("jsoncallback") + "(%s)" % json.dumps(s, indent=4))
            return 200
        else:
            s = {'response': 'response for cmd="%s" not completely implemented feature' % cmd}
            req.write(req.params.get("jsoncallback") + "(%s)" % json.dumps(s, indent=4))
            return 200

    filename = None
    filesize = 0

    s = {}

    if "submitter" in req.params.keys():

        submitter = req.params.get("submitter", "").split(';')[0]

        targetnodeid = req.params.get("targetnodeid_FOR_" + submitter, None)
        targetnode = None
        if targetnodeid:
            try:
                targetnode = q(Node).get(targetnodeid)
            except:
                msg = "metadata m_upload: targetnodeid='%s' for non-existant node for upload from '%s'" % (ustr(targetnodeid), ustr(req.ip))
                errors.append(msg)
                logg.error(msg)
        else:
            msg = "metadata m_upload could not find 'targetnodeid' for upload from '%s'" % ustr(req.ip)
            errors.append(msg)
            logg.error(msg)

        if not targetnode.has_data_access():
            msg = "m_upload: no access for user '%s' to node %s ('%s', '%s') from '%s'" % (
                user.name, ustr(targetnode.id), targetnode.name, targetnode.type, ustr(req.ip))
            logg.error(msg)
            errors.append(msg)

            s['errors'] = errors
            req.write("%s" % json.dumps(s, indent=4))
            return

        filename = None
        file_key = "m_upload_file_FOR_" + submitter

        if file_key in req.params:

            file = req.params[file_key]
            del req.params[file_key]

            filename = file.filename
            filesize = file.filesize
            filetempname = file.tempname

        else:
            msg = t(lang(req), "no file for this field submitted")
            errors.append(msg)

        if filename:

            diskname = normalizeFilename(filename)
            nodeFile = importFileToRealname(diskname, filetempname, prefix='m_upload_%s_' % (submitter, ), typeprefix="u_")

            if nodeFile:
                imported_filename = nodeFile.getName()
                imported_filesize = nodeFile.getSize()
                imported_filepath = nodeFile.retrieveFile()
                imported_filemimetype = nodeFile.getMimeType()
            else:
                msg = "metadata m_upload: could not create file node for request from '%s'" % (ustr(req.ip))
                errors.append(msg)
                logging.getLogger("backend").error(msg)

        if targetnode and filename:
            #todo: check this out later
            targetnode.addFile(nodeFile)

            filecount = len(getFilelist(targetnode, submitter)[0])
            targetnode.set(submitter, filecount)

            copy_report = t(lang(req), "uploaded file: %s; size: %d bytes") % (filename, filesize)

        else:
            copy_report = ""

    else:
        msg = "metadata m_upload: could not find submitter for request from '%s'" % (ustr(req.ip))
        errors.append(msg)
        logging.getLogger("backend").error(msg)

    s = {
        'errors': errors,
        'copy_report': copy_report,
    }

    req.write("%s" % json.dumps(s, indent=4))

    return 200
