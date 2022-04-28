# -*- coding: utf-8 -*-

# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import os
import subprocess
import re
import os.path
import shutil
import logging
import codecs
import fdfgen

import utils.utils as _utils_utils
from .workflow import WorkflowStep, getNodeWorkflow, getNodeWorkflowStep, registerStep
from core.translation import t, addLabels
from metadata.upload import getFilelist
from schema.schema import getMetaType, Metafield
from utils.fileutils import getImportDir
from utils.utils import join_paths, desc
from utils.date import format_date, now

import core.config as config
import utils.process

from core import db
from core import File

logg = logging.getLogger(__name__)


def register():
    #tree.registerNodeClass("workflowstep-addformpage", WorkflowStep_AddFormPage)
    registerStep("workflowstep_addformpage")
    addLabels(WorkflowStep_AddFormPage.getLabels())


def get_pdftk_fields_dump(path_to_pdf):
    return utils.process.Popen(("pdftk", path_to_pdf, "dump_data_fields"),
                               stdout=subprocess.PIPE).communicate()[0]


def parse_pdftk_fields_dump(s):
    field_dicts = []
    d = {}
    for line in [line.strip() for line in s.splitlines() if line.strip()]:
        if line.startswith('---'):
            if d:
                field_dicts.append(d)
                d = {}
        elif line.find(':') > 0:
            vals = line.split(':')
            d[vals[0].strip()] = ":".join(vals[1:]).strip()
    field_dicts.append(d)
    return field_dicts

TAG_RE = re.compile(r'<[^>]+>')


def remove_tags(text):
    return TAG_RE.sub('', text)


def fillPDFForm(formPdf, fields, outputPdf="filled.pdf", input_is_fullpath=False, editable=False):
    """
        fill given pdf file with form fields with given attributes and store result in pdf file
    """
    # build data file
    filenamebase = os.path.join(config.get('paths.tempdir'), _utils_utils.gen_secure_token(128))
    fdffilename = "{}.infdata.fdf".format(filenamebase)
    outputPdf = "{}.filled.pdf".format(filenamebase)
    try:
        with open(fdffilename, 'wb') as fdf_file:
            fdf_file.write(fdfgen.forge_fdf(fdf_data_strings=fields))

        # fill data in form pdf and generate pdf
        pdftkcmd = ["pdftk", formPdf, "fill_form", fdffilename, "output", outputPdf]
        if not editable:
            pdftkcmd.append("flatten")
        utils.process.call(pdftkcmd)

        if os.path.exists(fdffilename):
            os.remove(fdffilename)
    except Exception:
        logg.exception("exception in workflow step addformpage, error while filling pdf form, ignoring")

    return outputPdf if os.path.exists(outputPdf) else ""  # check if file created


def addPagesToPDF(prefile, pdffile):
    outfile = pdffile[:-4] + "1.pdf"
    try:
        utils.process.call(("pdftk", prefile, pdffile, "output", outfile))
        os.remove(prefile)
    except Exception:
        logg.exception("exception in workflow step addformpage, error while adding pages, ignoring")
    return outfile


class WorkflowStep_AddFormPage(WorkflowStep):
    """
        update given pdf-file and add some pre-pages
        pre-pages can use formular fields
    """

    def runAction(self, node, op=""):
        fnode = None
        for fnode in node.files:
            if fnode.filetype == "document":
                break

        def reformatAuthors(s):
            authors = s.strip().split(";")
            if len(authors) > 1:
                authors = ", ".join(authors[:-1]) + " and " + authors[-1]
            else:
                authors = authors[0]
            return authors

        # get pdf form appended to this workflow step through upload field 'upload_pdfform'
        current_workflow = getNodeWorkflow(node)
        current_workflow_step = getNodeWorkflowStep(node)
        formfilelist, formfilelist2 = getFilelist(current_workflow_step, 'upload_pdfform')

        pdf_fields_editable = current_workflow_step.get("pdf_fields_editable")
        pdf_form_separate = current_workflow_step.get("pdf_form_separate")
        pdf_form_overwrite = current_workflow_step.get("pdf_form_overwrite")

        if pdf_fields_editable.lower() in ["1", "true"]:
            pdf_fields_editable = True
        else:
            pdf_fields_editable = False

        if pdf_form_separate.lower() in ["1", "true"]:
            pdf_form_separate = True
        else:
            pdf_form_separate = False

        fields = []
        f_retrieve_path = None

        schema = getMetaType(node.schema)

        if formfilelist:
            # take newest (mtime)
            f_mtime, f_name, f_mimetype, f_size, f_type, f_retrieve_path, f = formfilelist[-1]

            for field_dict in parse_pdftk_fields_dump(get_pdftk_fields_dump(f_retrieve_path)):
                fieldname = field_dict.get('FieldName', None)
                if fieldname:
                    value = ''
                    if fieldname in dict(node.attrs.items()):
                        schemafield = schema.children.filter_by(name=fieldname).first()
                        value = schemafield.getFormattedValue(node)[1]
                        if fieldname.find('author') >= 0:
                            value = reformatAuthors(value)
                    elif fieldname.lower() == 'node.schema':
                        value = getMetaType(node.schema).getLongName()
                    elif fieldname.lower() == 'node.id':
                        value = unicode(node.id)
                    elif fieldname.lower() == 'node.type':
                        value = node.type
                    elif fieldname.lower() == 'date()':
                        value = format_date(now(), format='%d.%m.%Y')
                    elif fieldname.lower() == 'time()':
                        value = format_date(now(), format='%H:%M:%S')
                    elif fieldname.find("+") > 0:
                        for _fn in fieldname.split('+'):
                            value = node.get(_fn)
                            if value:
                                break
                    elif '[att:' in fieldname:
                        value = fieldname
                        while '[att:' in value:
                            m = re.search('(?<=\[att:)([^&\]]+)', value)
                            if m:
                                if m.group(0) == 'id':
                                    v = unicode(node.id)
                                elif m.group(0) == 'type':
                                    v = node.type
                                elif m.group(0) == 'schema':
                                    v = getMetaType(node.schema).getLongName()
                                else:
                                    schemafield = schema.children.filter_by(name=m.group(0)).first()
                                    v = schemafield.getFormattedValue(node)[0]
                                value = value.replace('[att:%s]' % (m.group(0)), v)
                    else:
                        logg.warning("workflowstep %s (%s): could not find attribute for pdf form field '%s' - node: '%s' (%s)",
                                       current_workflow_step.name, current_workflow_step.id, fieldname, node.name, node.id)
                    fields.append((fieldname, remove_tags(desc(value))))

        if not pdf_form_separate and fnode and f_retrieve_path and os.path.isfile(f_retrieve_path):
            pages = fillPDFForm(f_retrieve_path, fields, input_is_fullpath=True, editable=pdf_fields_editable)
            if pages == "":  # error in pdf creation -> forward to false operation
                logg.error("workflowstep %s (%s): could not create pdf file - node: '%s' (%s)" %
                           (current_workflow_step.name, current_workflow_step.id, node.name, node.id))
                self.forward(node, False)
                return
            origname = fnode.abspath
            outfile = addPagesToPDF(pages, origname)

            for f in node.files:
                node.files.remove(f)
            fnode.path = outfile.replace(config.get("paths.datadir"), "")
            node.files.append(fnode)
            node.files.append(File(origname, 'upload', 'application/pdf'))  # store original filename
            node.event_files_changed()
            db.session.commit()
            logg.info("workflow '%s' (%s), workflowstep '%s' (%s): added pdf form to pdf (node '%s' (%s)) fields: %s",
                current_workflow.name, current_workflow.id, current_workflow_step.name, current_workflow_step.id, node.name, node.id, fields)
            
        elif pdf_form_separate and f_retrieve_path and os.path.isfile(f_retrieve_path):
            pages = fillPDFForm(f_retrieve_path, fields, input_is_fullpath=True, editable=pdf_fields_editable)
            if pages == "":  # error in pdf creation -> forward to false operation
                logg.error("workflowstep %s (%s): could not create pdf file - node: '%s' (%s)" %
                           (current_workflow_step.name, current_workflow_step.id, node.name, node.id))
                self.forward(node, False)
                return
            importdir = getImportDir()
            try:
                # Build the filename of the form file on disk.
                # Note that the filename is underscore separated
                # and the part after the last underscore is
                # visible to the user when the file gets
                # emailed in ``email.py``.
                new_form_path = [str(node.id), f_name]
                if pdf_form_overwrite:
                    new_form_path.insert(1, _utils_utils.gen_secure_token(128))
                new_form_path = join_paths(importdir, "_".join(new_form_path))
                # copy new file and remove tmp
                shutil.copy(pages, new_form_path)
                if os.path.exists(pages):
                    os.remove(pages)
            except Exception:
                logg.exception("workflowstep %s (%s): could not copy pdf form to import directory - node: '%s' (%s), import directory: '%s'",
                             current_workflow_step.name, current_workflow_step.id, node.name, node.id, importdir)
            found = 0
            for fn in node.files:
                if fn.abspath == new_form_path:
                    found = 1
                    break
            if found == 0 or (found == 1 and not pdf_form_overwrite):
                node.files.append(File(new_form_path, 'metafield-upload.upload_pdfform', 'application/pdf'))
                db.session.commit()

            logg.info(
                "workflow '%s' (%s), workflowstep '%s' (%s): added separate pdf form to node (node '%s' (%s)) fields: %s, path: '%s'",
                current_workflow.name, current_workflow.id, current_workflow_step.name,
                current_workflow_step.id, node.name, node.id, fields, new_form_path)
        else:
            logg.warning("workflowstep %s (%s): could not process pdf form - node: '%s' (%s)",
                           current_workflow_step.name, current_workflow_step.id, node.name, node.id)

        self.forward(node, True)

    def show_workflow_node(self, node, req):
        self.forward(node, True)

    def metaFields(self, lang=None):
        ret = list()
        field = Metafield("upload_pdfform")
        field.set("label", t(lang, "workflowstep-addformpage_label_upload_pdfform"))
        field.set("type", "upload")
        ret.append(field)

        field = Metafield("pdf_fields_editable")
        field.set("label", t(lang, "workflowstep-addformpage_label_pdf_fields_editable"))
        field.set("type", "check")
        ret.append(field)

        field = Metafield("pdf_form_separate")
        field.set("label", t(lang, "workflowstep-addformpage_label_pdf_form_separate"))
        field.set("type", "check")
        ret.append(field)

        field = Metafield("pdf_form_overwrite")
        field.set("label", t(lang, "workflowstep-addformpage_label_pdf_overwrite"))
        field.set("type", "check")
        ret.append(field)
        return ret

    @staticmethod
    def getLabels():
        return {"de":
                [
                    ("workflowstep-addformpage", u"PDF-Seiten hinzufügen"),
                    ("workflowstep-addformpage_label_upload_pdfform", "Eine PDF-Form hier hochladen"),
                    ("workflowstep-addformpage_label_pdf_fields_editable", "PDF-Form-Felder editierbar"),
                    ("workflowstep-addformpage_label_pdf_form_separate", u"PDF-Form separat an Knoten anhängen"),
                    ("workflowstep-addformpage_label_pdf_overwrite", u"PDF-Form überschreiben"),
                ],
                "en":
                [
                    ("workflowstep-addformpage", "add PDF pages"),
                    ("workflowstep-addformpage_label_upload_pdfform", "Upload one PDF form here"),
                    ("workflowstep-addformpage_label_pdf_fields_editable", "PDF form fields editable"),
                    ("workflowstep-addformpage_label_pdf_form_separate", "append PDF form separately to node"),
                    ("workflowstep-addformpage_label_pdf_overwrite", "Overwrite existing form"),
                ]
                }
