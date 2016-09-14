# -*- coding: utf-8 -*-
"""
 mediatum - a multimedia content repository

 Copyright (C) 2007 Arne Seifert <seiferta@in.tum.de>
 Copyright (C) 2007 Matthias Kramm <kramm@in.tum.de>
 Copyright (C) 2012 Werner Neudenberger <neudenberger@ub.tum.de>


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
import os
import logging
import random

import core.users as users
import core.athana as athana
import core.config as config

from .workflow import WorkflowStep, getNodeWorkflow, getNodeWorkflowStep, registerStep
from core.translation import t, lang, addLabels
from utils.utils import getMimeType
from utils.fileutils import importFileToRealname
from utils.date import format_date

from metadata.upload import getFilelist

from reportlab.lib.units import cm
from schema.schema import Metafield
from core import File
from core import Node
from core import db

q = db.query

try:
    import pyPdf
    PYPDF_MODULE_PRESENT = True
except:
    PYPDF_MODULE_PRESENT = False

if PYPDF_MODULE_PRESENT:
    from .logoadd_utils import get_pdf_pagesize, get_pdf_pagecount, \
        get_pdf_dimensions, get_pdf_page_image, \
        get_pic_size, get_pic_info, \
        get_pic_dpi, place_pic, parse_printer_range, \
        getGridBuffer, build_logo_overlay_pdf


logg = logging.getLogger(__name__)


def check_context():
    webcontexts = athana.contexts
    if (not filter(lambda x: x.name == '/wfs_addpic2pdf', webcontexts)) and athana.GLOBAL_ROOT_DIR != "no-root-dir-set":
        print 'going to add context wfs_addpic2pdf'
        webcontext = athana.addContext("/wfs_addpic2pdf", ".")
        webcontext_file = webcontext.addFile("workflow/addpic2pdf.py")
        webcontext_file.addHandler("handle_request").addPattern("/.*")

check_context()


def getPdfFilepathForProcessing(workflowstep_node, node):
    res = ([f.abspath for f in node.files if f.base_name.startswith('addpic2pdf_%s_node_%s_' % (
        unicode(workflowstep_node.id), unicode(node.id))) and f.filetype.startswith('p_document')] +
           [f.abspath for f in node.files if f.filetype.startswith('document')])[0]
    return res


def copyDictValues(dsource, dtarget, keylist, skip_empty=True):
    for k in keylist:
        v = dsource.get(k, "")
        dtarget[k] = v
    return dtarget


KEEP_PARAMS = ['input_current_page']
startpageno = 0  # page of the pdf that will be shown on page load
ADD_NBSP = 1


def register():
    #tree.registerNodeClass("workflowstep-addpic2pdf", WorkflowStep_AddPic2Pdf)
    registerStep("workflowstep_addpic2pdf")
    addLabels(WorkflowStep_AddPic2Pdf.getLabels())


class WorkflowStep_AddPic2Pdf(WorkflowStep):

    def show_workflow_node(self, node, req, data=None):

        check_context()

        user = users.getUserFromRequest(req)

        current_workflow = getNodeWorkflow(node)
        current_workflow_step = getNodeWorkflowStep(node)

        FATAL_ERROR = False
        FATAL_ERROR_STR = ""

        if "gotrue" in req.params:

            if not PYPDF_MODULE_PRESENT:
                del req.params['gotrue']
                return self.show_workflow_node(node, req)

            radio_apply_reset_accept = req.params.get('radio_apply_reset_accept', '')

            if radio_apply_reset_accept == 'reset':
                for f in node.files:
                    f_name = f.base_name
                    if f_name.startswith('addpic2pdf_%s_node_%s_' %
                                         (unicode(current_workflow_step.id), unicode(node.id))) and f.filetype.startswith('p_document'):
                        logg.info("workflow step addpic2pdf(%s): going to remove file '%s' from node '%s' (%s) for request from user '%s' (%s)",
                            current_workflow_step.id, f_name, node.name, node.id, user.login_name, req.ip)
                        node.files.remove(f)
                        db.session.commit()
                        try:
                            os.remove(f.abspath)
                        except:
                            logg.exception("exception in workflow setep addpic2pdf, removing file failed, ignoring")

                del req.params['gotrue']
                return self.show_workflow_node(node, req)

            elif radio_apply_reset_accept == 'accept':

                p_document_files = [f for f in node.files if f.filetype == 'p_document' and f.base_name.startswith(
                    'addpic2pdf_%s_node_%s_' % (unicode(current_workflow_step.id), unicode(node.id)))]

                if len(p_document_files) > 0:

                    p_document_file = p_document_files[0]

                    document_file = [f for f in node.files if f.filetype == 'document'][0]

                    o_document_file = File(document_file.path, 'o_document', document_file.mimetype)

                    node.files.remove(document_file)
                    node.files.append(o_document_file)
                    db.session.commit()
                    o_document_name = o_document_file.base_name

                    for f in node.files:
                        if f.filetype in ['thumb', 'fileinfo', 'fulltext'] or f.filetype.startswith('present'):
                            if os.path.splitext(f.base_name)[0] == os.path.splitext(o_document_name)[0]:
                                new_f = File(f.path, 'o_' + f.filetype, f.mimetype)
                                node.files.remove(f)
                                node.files.append(new_f)

                    new_document_file = File(p_document_file.path, 'document', p_document_file.mimetype)
                    node.files.remove(p_document_file)
                    node.files.append(new_document_file)
                    db.session.commit()
                    node.event_files_changed()

                del req.params['gotrue']
                return self.forwardAndShow(node, True, req)

            elif radio_apply_reset_accept == 'apply':

                drag_logo_fullname = req.params.get("input_drag_logo_fullname", None)

                if not drag_logo_fullname:
                    req.params["addpic2pdf_error"] = "%s: %s" % (
                        format_date().replace('T', ' - '), t(lang(req), "admin_wfstep_addpic2pdf_no_logo_selected"))
                    del req.params['gotrue']
                    return self.show_workflow_node(node, req)

                drag_logo_filepath = [f.abspath for f in current_workflow_step.files if f.base_name == drag_logo_fullname][0]

                pos_cm = req.params.get("input_poffset_cm", "0, 0")
                x_cm, y_cm = [float(x.strip()) for x in pos_cm.split(",")]

                pdf_in_filepath = getPdfFilepathForProcessing(current_workflow_step, node)

                current_pageno = int(req.params.get("input_current_page", "0").strip())

                radio_select_targetpages = req.params.get("radio_select_targetpages", "").strip()
                input_select_targetpages = req.params.get("input_select_targetpages", "").strip()

                printer_range = []
                page_count = get_pdf_pagecount(pdf_in_filepath)
                _parser_error = False

                try:
                    if radio_select_targetpages == "current_page":
                        printer_range = [current_pageno]
                    elif radio_select_targetpages == "all":
                        printer_range = range(0, page_count)
                    elif radio_select_targetpages == "pair":
                        printer_range = [x for x in range(0, page_count) if x % 2]
                        if input_select_targetpages:
                            printer_range = [x for x in printer_range if x in parse_printer_range(
                                input_select_targetpages, maximum=page_count + 1)]
                    elif radio_select_targetpages == "impair":
                        printer_range = [x for x in range(0, page_count) if not x % 2]
                        if input_select_targetpages:
                            printer_range = [x for x in printer_range if x in parse_printer_range(
                                input_select_targetpages, maximum=page_count + 1)]
                    elif radio_select_targetpages == "range_only" and input_select_targetpages:
                        printer_range = parse_printer_range(input_select_targetpages, maximum=page_count + 1)
                except ValueError as e:
                    _parser_error = True

                if _parser_error:
                    req.params["addpic2pdf_error"] = "%s: %s" % (
                        format_date().replace('T', ' - '), t(lang(req), "admin_wfstep_addpic2pdf_printer_range_error"))
                    del req.params['gotrue']
                    return self.show_workflow_node(node, req)

                printer_range = map(int, list(printer_range))

                if not printer_range:
                    req.params["addpic2pdf_error"] = "%s: %s" % (
                        format_date().replace('T', ' - '), t(lang(req), "admin_wfstep_addpic2pdf_printer_range_selected_empty"))
                    del req.params['gotrue']
                    return self.show_workflow_node(node, req)

                x = x_cm * cm  # cm = 28.346456692913385
                y = y_cm * cm

                pic_dpi = get_pic_info(drag_logo_filepath).get('dpi', None)

                scale = 1.0

                if pic_dpi:
                    dpi_x, dpi_y = pic_dpi
                    if dpi_x != dpi_y:
                        req.params["addpic2pdf_error"] = "%s: %s" % (
                            format_date().replace('T', ' - '), t(lang(req), "admin_wfstep_addpic2pdf_logo_dpix_dpiy"))
                    dpi = int(dpi_x)
                    if dpi == 72:
                        scale = 1.0
                    else:
                        scale = 1.0 * 72.0 / dpi
                else:
                    dpi = 300
                    scale = 1.0 * 72.0 / dpi
                    #dpi = 72
                    #scale = 1.0

                tmppath = config.get("paths.datadir") + "tmp/"
                date_str = format_date().replace('T', '-').replace(' ', '').replace(':', '-')
                filetempname = tmppath + \
                    "temp_addpic_pdf_wfs_%s_node_%s_%s_%s_.pdf" % (
                        unicode(current_workflow_step.id), unicode(node.id), date_str, unicode(random.random()))

                url = req.params.get('input_drag_logo_url', '')

                fn_out = filetempname

                build_logo_overlay_pdf(pdf_in_filepath, drag_logo_filepath, fn_out, x, y, scale=scale,
                                       mask='auto', pages=printer_range, follow_rotate=True, url=(" " * ADD_NBSP) + url)

                for f in node.files:
                    f_name = f.base_name
                    if f_name.startswith('addpic2pdf_%s_node_%s_' %
                                         (unicode(current_workflow_step.id), unicode(node.id), )) and f.filetype.startswith('p_document'):
                        logg.info("workflow step addpic2pdf(%s): going to remove file '%s' from node '%s' (%s) for request from user '%s' (%s)",
                            current_workflow_step.id, f_name, node.name, node.id, user.login_name, req.ip)
                        node.files.remove(f)
                        db.session.commit()
                        try:
                            os.remove(f.abspath)
                        except:
                            pass
                        break

                date_str = format_date().replace('T', '-').replace(' ', '').replace(':', '-')
                nodeFile = importFileToRealname("_has_been_processed_%s.pdf" % (date_str), filetempname, prefix='addpic2pdf_%s_node_%s_' % (
                    unicode(current_workflow_step.id), unicode(node.id), ), typeprefix="p_")
                node.files.append(nodeFile)
                db.session.commit()
                try:
                    os.remove(filetempname)
                except:
                    pass

                del req.params['gotrue']
                return self.show_workflow_node(node, req)

        if "gofalse" in req.params:
            return self.forwardAndShow(node, False, req)

        # part of show_workflow_node not handled by "gotrue" and "gofalse"

        try:
            pdf_filepath = [f.abspath for f in node.files if f.filetype.startswith('document')][0]
            error_no_pdf = False
        except:
            error_no_pdf = t(lang(req), "admin_wfstep_addpic2pdf_no_pdf_document_for_this_node")

        if not PYPDF_MODULE_PRESENT or error_no_pdf:
            error = ""
            if not PYPDF_MODULE_PRESENT:
                error += t(lang(req), "admin_wfstep_addpic2pdf_no_pypdf")
            if error_no_pdf:
                error += error_no_pdf
            pdf_dimensions = {'d_pageno2size': {0: [595.275, 841.889]}, 'd_pageno2rotate': {0: 0}}  # A4
            keep_params = copyDictValues(req.params, {}, KEEP_PARAMS)
            context = {"key": req.params.get("key", req.session.get("key", "")),
                       "error": error,

                       "node": node,
                       "files": node.files,
                       "wfs": current_workflow_step,
                       "wfs_files": [],

                       "logo_info": {},
                       "logo_info_list": [],

                       "getImageSize": lambda x: (0, 0),
                       "pdf_page_count": 0,
                       "pdf_dimensions": pdf_dimensions,
                       "json_pdf_dimensions": json.dumps(pdf_dimensions),
                       "keep_params": json.dumps(keep_params),
                       "startpageno": 0,

                       "FATAL_ERROR": 'true',

                       "user": users.getUserFromRequest(req),
                       "prefix": self.get("prefix"),
                       "buttons": self.tableRowButtons(node)}

            return req.getTAL("workflow/addpic2pdf.html", context, macro="workflow_addpic2pdf")
        try:
            pdf_dimensions = get_pdf_dimensions(pdf_filepath)
            pdf_pagecount = get_pdf_pagecount(pdf_filepath)
        except Exception as e:
            logg.exception("exception in workflow step addpic2pdf(%s)", current_workflow_step.id)
            pdf_dimensions = {'d_pages': 0, 'd_pageno2size': (0, 0), 'd_pageno2rotate': 0}
            pdf_pagecount = 0
            FATAL_ERROR = True
            FATAL_ERROR_STR += " - %s" % (unicode(e))

        #wfs_files = [f for f in current_workflow_step.getFiles() if os.path.isfile(f.retrieveFile())]

        wfs_files0, wfs_files = getFilelist(current_workflow_step, 'logoupload')

        url_mapping = [line.strip()
                       for line in current_workflow_step.get("url_mapping").splitlines() if line.strip() and line.find("|") > 0]
        url_mapping = dict(map(lambda x: (x[0].strip(), x[1].strip()), [line.split("|", 1) for line in url_mapping]))

        logo_info = {}
        logo_info_list = []
        for f in [f for f in wfs_files if f.base_name.startswith('m_upload_logoupload')]:
            f_path = f.abspath

            try:
                _size = list(get_pic_size(f_path))
                _dpi = get_pic_dpi(f_path)
            except Exception as e:
                logg.exception("exception in workflow step addpic2pdf(%s)", current_workflow_step.id)
                FATAL_ERROR = True
                FATAL_ERROR_STR += (" - ERROR loading logo '%s'" % f_path) + unicode(e)
                continue

            logo_filename = f.base_name

            logo_url = ""
            for key in url_mapping:
                if logo_filename.find(key) >= 0:
                    logo_url = url_mapping[key]
                    break

            logo_info[logo_filename.encode('utf-8')] = {'size': _size, 'dpi': _dpi, 'url': logo_url.encode('utf-8')}
            if _dpi == 'no-info':
                _dpi = 72.0
            logo_info_list.append({'size': _size, 'dpi': _dpi, 'url': logo_url.encode('utf-8')})

        if len(logo_info) == 0:
            logg.error("workflow step addpic2pdf(%s): Error: no logo images found", current_workflow_step.id)
            FATAL_ERROR = True
            FATAL_ERROR_STR += " - Error: no logo images found"

        keep_params = copyDictValues(req.params, {}, KEEP_PARAMS)

        context = {"key": req.params.get("key", req.session.get("key", "")),
                   "error": req.params.get('addpic2pdf_error', ''),

                   "node": node,
                   "files": node.files,
                   "wfs": current_workflow_step,
                   "wfs_files": wfs_files,

                   "logo_info": logo_info,
                   "logo_info_list": logo_info_list,

                   "getImageSize": get_pic_size,
                   "pdf_page_count": pdf_pagecount,
                   "pdf_dimensions": pdf_dimensions,
                   "json_pdf_dimensions": json.dumps(pdf_dimensions),
                   "keep_params": json.dumps(keep_params),
                   "startpageno": startpageno,

                   "FATAL_ERROR": {False: 'false', True: 'true'}[bool(FATAL_ERROR)],

                   "user": users.getUserFromRequest(req),
                   "prefix": self.get("prefix"),
                   "buttons": self.tableRowButtons(node)}

        if FATAL_ERROR:
            context["error"] += " - %s" % (FATAL_ERROR_STR)

        return req.getTAL("workflow/addpic2pdf.html", context, macro="workflow_addpic2pdf")

    def metaFields(self, lang=None):

        if not PYPDF_MODULE_PRESENT:
            field = Metafield("infotext")
            field.set("label", t(lang, "admin_wfstep_addpic2pdf_hint"))
            field.set("type", "label")
            field.set("value", t(lang, "admin_wfstep_addpic2pdf_no_pypdf"))
            return [field]

        ret = []

        field = Metafield("prefix")
        field.set("label", t(lang, "admin_wfstep_text_before_data"))
        field.set("type", "memo")
        ret.append(field)

        field = Metafield("logoupload")
        field.set("label", t(lang, "admin_wfstep_addpic2pdf_upload01"))
        field.set("type", "upload")
        ret.append(field)

        field = Metafield("url_mapping")
        field.set("label", t(lang, "admin_wfstep_addpic2pdf_label_url_mapping"))
        field.set("type", "memo")
        ret.append(field)
        return ret

    @staticmethod
    def getLabels():
        return {"de":
                [
                    ("workflowstep-addpic2pdf", 'AddPictureToPDF'),

                    ("admin_wfstep_addpic2pdf_hint", 'Hinweis'),
                    ("admin_wfstep_addpic2pdf_no_pypdf",
                     '<b style="color:red;">WARNUNG:</b> Python-Modul pyPdf ist nicht installiert - dieser Workflow-Schritt ist nicht funktional'),

                    ("admin_wfstep_addpic2pdf_no_pdf_document_for_this_node",
                     u'Kein PDF-Document vom Typ "document" gefunden - dieser Workflow-Schritt ist für diesen Knoten nicht funktional'),
                    ("admin_wfstep_addpic2pdf_no_logo_selected", u'Es wurde kein Bild zum Einfügen ausgewählt'),
                    ("admin_wfstep_addpic2pdf_printer_range_error", 'Fehler bei der Definition des Seitenbereiches'),
                    ("admin_wfstep_addpic2pdf_printer_range_selected_empty", u'Der gewählte Seitenbereich ist leer'),
                    ("admin_wfstep_addpic2pdf_logo_dpix_dpiy",
                     u'Das gewählte Bild hat unterschiedliche dpi-Werte in x- und y-Richtung: Darstellungsfehler'),

                    ("admin_wfstep_addpic2pdf_upload01", 'Logo hier hochladen'),
                    ("admin_wfstep_addpic2pdf_label_url_mapping", 'URL-Mapping (Separator: |)'),

                    ("admin_wfstep_addpic2pdf_logo_none", 'Nichts'),

                    ("admin_wfstep_addpic2pdf_select_page_to_preview", 'Vorschau (Seite)'),

                    ("admin_wfstep_addpic2pdf_range_only_current_page", 'Nur aktuelle Seite'),
                    ("admin_wfstep_addpic2pdf_all_pages", 'Alle Seiten'),
                    ("admin_wfstep_addpic2pdf_pair", 'Gerade Seiten'),
                    ("admin_wfstep_addpic2pdf_impair", 'Ungerade Seiten'),
                    ("admin_wfstep_addpic2pdf_only_range", 'Nur Bereich'),

                    ("admin_wfstep_addpic2pdf_define_range", 'Bereich festlegen:<br/>(Beispiel: 1-10;12;17;30-)'),

                    ("admin_wfstep_addpic2pdf_button_accept_image_position", 'Bild in PDF hineindrucken'),
                    ("admin_wfstep_addpic2pdf_button_back_to_original", u'Zurücksetzen zum Original'),
                    ("admin_wfstep_addpic2pdf_button_continue", 'Weiter'),

                    ("admin_wfstep_addpic2pdf_cb_grid", 'Gitter'),
                    ("admin_wfstep_addpic2pdf_cb_logo_above_grid", u'Bild über Gitter'),
                    ("admin_wfstep_addpic2pdf_link_processed", 'in Bearbeitung'),
                    ("admin_wfstep_addpic2pdf_link_original", 'Original'),

                    ("admin_wfstep_addpic2pdf_true_button", 'Weiter'),

                    ("admin_wfstep_addpic2pdf_false_button", 'Option B'),

                    ("admin_wfstep_addpic2pdf_grid_origin_label", 'Nullpunkt'),
                ],
                "en":
                [
                    ("workflowstep-addpic2pdf", 'AddPictureToPDF'),

                    ("admin_wfstep_addpic2pdf_hint", 'Hint'),
                    ("admin_wfstep_addpic2pdf_no_pypdf",
                     '<b style="color:red;">WARNING:</b> Python module pyPdf is not installed - this workflow step is not functional'),

                    ("admin_wfstep_addpic2pdf_no_pdf_document_for_this_node",
                     'No PDF of type "document" found - this workflow step is not functional for this node'),
                    ("admin_wfstep_addpic2pdf_no_logo_selected", 'No picture has been selected'),
                    ("admin_wfstep_addpic2pdf_printer_range_error", 'Error in page range definition'),
                    ("admin_wfstep_addpic2pdf_printer_range_selected_empty", 'The selected page range is empty'),
                    ("admin_wfstep_addpic2pdf_logo_dpix_dpiy",
                     'The chosen picture has different resolutions (dpi) in x and y direction: scale errors are possible'),

                    ("admin_wfstep_addpic2pdf_upload01", 'Upload logo here'),
                    ("admin_wfstep_addpic2pdf_label_url_mapping", 'URL mapping (separator: |)'),

                    ("admin_wfstep_addpic2pdf_logo_none", 'None'),

                    ("admin_wfstep_addpic2pdf_select_page_to_preview", 'Select preview page'),

                    ("admin_wfstep_addpic2pdf_range_only_current_page", 'Only current page'),
                    ("admin_wfstep_addpic2pdf_all_pages", 'All pages'),
                    ("admin_wfstep_addpic2pdf_pair", 'Pair (with range)'),
                    ("admin_wfstep_addpic2pdf_impair", 'Impair (with range)'),
                    ("admin_wfstep_addpic2pdf_only_range", 'Only range'),

                    ("admin_wfstep_addpic2pdf_define_range", 'Define range:<br/>(example: 1-10;12;17;30-)'),

                    ("admin_wfstep_addpic2pdf_button_accept_image_position", 'Print picture into PDF'),
                    ("admin_wfstep_addpic2pdf_button_back_to_original", 'Reset to original'),
                    ("admin_wfstep_addpic2pdf_button_continue", 'Continue'),

                    ("admin_wfstep_addpic2pdf_cb_grid", 'Grid'),
                    ("admin_wfstep_addpic2pdf_cb_logo_above_grid", 'Picture above grid'),
                    ("admin_wfstep_addpic2pdf_link_processed", 'Currently processed'),
                    ("admin_wfstep_addpic2pdf_link_original", 'Original'),

                    ("admin_wfstep_addpic2pdf_true_button", 'Continue'),

                    ("admin_wfstep_addpic2pdf_false_button", 'Option B'),

                    ("admin_wfstep_addpic2pdf_grid_origin_label", 'Origin'),
                ]
                }


def serve_file(req, filepath):

    if 'mimetype' in req.params:
        mimetype = req.params.get('mimetype')
    elif filepath.lower().endswith('.html') or filepath.lower().endswith('.htm'):
        mimetype = 'text/html'
    else:
        mimetype = getMimeType(filepath)

    req.reply_headers['Content-Type'] = mimetype

    tmppath = config.get("paths.datadir") + "tmp/"

    abspath = os.path.join(tmppath, filepath)

    if os.path.isfile(abspath):
        filesize = os.path.getsize(abspath)
        req.sendFile(abspath, mimetype, force=1)
        return 200, filesize, abspath  # ok
    else:
        return 404, 0, abspath  # not found


def read_serve_file(req, filepath, remove_after_sending=False):

    if 'mimetype' in req.params:
        mimetype = req.params.get('mimetype')
    elif filepath.lower().endswith('.html') or filepath.lower().endswith('.htm'):
        mimetype = 'text/html'
    else:
        mimetype = getMimeType(filepath)

    req.reply_headers['Content-Type'] = mimetype

    abspath = filepath

    if os.path.isfile(abspath):

        f = open(abspath, "rb")
        s = f.read()
        f.close()
        if remove_after_sending:
            os.remove(abspath)
        req.write(s)
        return 200, len(s), abspath  # ok
    else:
        return 404, 0, abspath  # not found


def handle_request(req):

    errors = []

    user = users.getUserFromRequest(req)

    if not PYPDF_MODULE_PRESENT:
        return

    if req.path.startswith("/serve_page/"):

        node_id = req.params.get("node_id", None)
        if node_id:
            node = q(Node).get(node_id)
            if node is None:
                return 404  # not found
        else:
            return 404  # not found

        current_workflow = getNodeWorkflow(node)
        current_workflow_step = getNodeWorkflowStep(node)

        if not current_workflow_step:
            return 404  # not found
        current_workflow_step_children_ids = [n.id for n in current_workflow_step.children]
        if node.id not in current_workflow_step_children_ids:
            return 403  # forbidden

        # XXX: WTF?!
        if False:  # and not access.hasAccess(node, "read"):
            req.params["addpic2pdf_error"] = "%s: %s" % (
                format_date().replace('T', ' - '), t(lang(req), "admin_wfstep_addpic2pdf_no_access"))
            logg.info("workflow step addpic2pdf(%s): no access to node %s for request from user '%s' (%s)",
                current_workflow_step.id, node.id, user.name, req.ip)
            return 403  # forbidden

        if req.path == '/serve_page/document.pdf':
            filepath = [f.abspath for f in node.filrd if f.filetype.startswith('document')][0]
            return_code, file_size, abspath = serve_file(req, filepath)
            return return_code

        if req.path == '/serve_page/p_document.pdf':
            filepath = (
                [f.abspath for f in node.files if f.filetype.startswith('p_document') and f.base_name.startswith(
                    'addpic2pdf_%s_node_%s_' % (unicode(current_workflow_step.id), unicode(node.id), )) and f.filetype.startswith('p_document')]
                + [f.abspath for f in node.files if f.filetype.startswith('document')]
            )[0]

            return_code, file_size, abspath = serve_file(req, filepath)
            return return_code

        pageno = req.path.replace("/serve_page/", "")
        pageno = pageno.split('?')[0]

        pdf_in_filepath = getPdfFilepathForProcessing(current_workflow_step, node)

        pdf_page_image_fullpath = get_pdf_page_image(pdf_in_filepath, pageno)

        return_code, file_size, abspath = read_serve_file(req, pdf_page_image_fullpath, remove_after_sending=True)

        return return_code

    if req.path.startswith("/grid"):
        pdf_w = float(req.params.get('pdf_w', 595.275))
        pdf_h = float(req.params.get('pdf_h', 841.890))

        thumb_w = float(req.params.get('thumb_w', 424))
        thumb_h = float(req.params.get('thumb_h', 600))

        dpi_w = float(req.params.get('dpi_w', 72.0))
        dpi_h = float(req.params.get('dpi_h', 72.0))

        thick = int(req.params.get('thick', 5))

        orig = req.params.get('orig', "bottom_left")

        rotate = int(req.params.get('rotate', "0"))

        pdf_size = (pdf_w, pdf_h)
        thumb_size = (thumb_w, thumb_h)
        dpi = (dpi_w, dpi_h)

        orig_message = t(lang(req), "admin_wfstep_addpic2pdf_grid_origin_label")

        f = getGridBuffer(pdf_size, thumb_size, dpi, thick=5, orig=["top_left", "bottom_left"][1], orig_message=orig_message, rotate=rotate)
        s = f.getvalue()
        req.write(s)
        req.write('')
        req.reply_headers['Content-Type'] = "image/png"
        return 200

    # part handle_request not matched by "/serve_page/" and "/grid"

    nodeid = req.params.get("selection_name", None)
    node = None

    if nodeid:
        nodeid = nodeid.replace("pdfpage_select_for_node_", "")
        node = q(Node).get(nodeid)
        if node is None:
            msg = "workflowstep addpic2pdf: nodeid='%s' for non-existant node for upload from '%s'" % (unicode(nodeid), req.ip)
            errors.append(msg)
            logg.error(msg)
            return 404  # not found
    else:
        msg = "workflowstep addpic2pdf: could not find 'nodeid' for upload from '%s'" % req.ip
        errors.append(msg)
        logg.error(msg)
        return 404  # not found

    try:
        current_workflow = getNodeWorkflow(node)
        current_workflow_step = getNodeWorkflowStep(node)
    except:
        return 403  # forbidden

    if False:  # not access.hasAccess(node, "read"):
        req.params["addpic2pdf_error"] = "%s: %s" % (format_date().replace('T', ' - '), t(lang(req), "admin_wfstep_addpic2pdf_no_access"))
        logg.info("workflow step addpic2pdf(%s): no access to node %s for request from user '%s' (%s)",
            current_workflow_step.id, node.id, user.name, req.ip)
        return 403  # forbidden

    pdf_in_filepath = getPdfFilepathForProcessing(current_workflow_step, node)
    pdf_page_image_url = get_pdf_page_image(pdf_in_filepath, req.params.get("pageno", "0"), path_only=True)

    s = {'pdf_page_image_url': pdf_page_image_url}

    req.write(req.params.get("jsoncallback") + "(%s)" % json.dumps(s, indent=4))

    return 200
