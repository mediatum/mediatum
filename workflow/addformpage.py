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
import fdfgen

from mediatumtal import tal as _tal

import utils.utils as _utils_utils
from .workflow import WorkflowStep
from .workflow import registerStep
from core.translation import addLabels
from schema.schema import getMetaType
import utils.fileutils as _fileutils
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


def fillPDFForm(formPdf, fields, editable):
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

    return outputPdf if os.path.exists(outputPdf) else None  # check if file created


def addPagesToPDF(prefile, pdffile):
    outfile = pdffile[:-4] + "1.pdf"
    try:
        utils.process.call(("pdftk", prefile, pdffile, "output", outfile))
        os.remove(prefile)
    except Exception:
        logg.exception("exception in workflow step addformpage, error while adding pages, ignoring")
    return outfile


def _get_fields_from_from_and_node(pdf_form_path, node):
    """
    Generate a list of pdf form values (a list of dicts, neede by `fdf_gen`),
    based on the form names in the given pdf file and the attributes of the given node.
    """

    # get list of fields from pdftk
    field_lines = utils.process.Popen(("pdftk", pdf_form_path, "dump_data_fields"),
                                      stdout=subprocess.PIPE).communicate()[0].splitlines()
    field_names = set()
    for line in filter(None,(line.strip() for line in field_lines)):
        if ":" in line:
            key, value = line.split(":", 1)
            if key.strip()=="FieldName":
                field_names.add(value.strip())
    field_names.discard("")

    # get field values from node
    schema = getMetaType(node.schema)
    get_formatted_value = lambda name: schema.children.filter_by(name=name).one().getFormattedValue(node)
    for fieldname in field_names:
        if fieldname in node.attrs:
            value = get_formatted_value(fieldname)[1]
            if "author" in fieldname:
                value = value.strip()
                if ";" in value:
                    value = value.split(";")
                    value = " and ".format(", ".join(value[:-1]), value[-1])
        elif fieldname.lower() == 'node.schema':
            value = schema.getLongName()
        elif fieldname.lower() == 'node.id':
            value = unicode(node.id)
        elif fieldname.lower() == 'node.type':
            value = node.type
        elif fieldname.lower() == 'date()':
            value = format_date(now(), format='%d.%m.%Y')
        elif fieldname.lower() == 'time()':
            value = format_date(now(), format='%H:%M:%S')
        elif "+" in fieldname:
            for fn in fieldname.split('+'):
                value = node.get(fn)
                if value:
                    break
            else:
                value = ""
        elif '[att:' in fieldname:
            value = fieldname
            while '[att:' in value:
                m = re.search('[[]att:([^&\]]+)', value)
                if not m:
                    continue
                m = m.group(1)
                if m == 'id':
                    v = unicode(node.id)
                elif m == 'type':
                    v = node.type
                elif m == 'schema':
                    v = schema.getLongName()
                else:
                    v = get_formatted_value(m)[0]
                value = value.replace('[att:{}]'.format(m), v)
        else:
            value = ""
            logg.warning("could not find attribute for pdf form field '%s' - node: '%s' (%s)",
                         fieldname, node.name, node.id)
        yield (fieldname, re.sub(r'<[^>]+>', '', desc(value)))


class WorkflowStep_AddFormPage(WorkflowStep):
    """
        update given pdf-file and add some pre-pages
        pre-pages can use formular fields
    """

    def runAction(self, node, op=""):

        # get workflow step options
        pdf_fields_editable = self.get("pdf_fields_editable").lower() in ("1", "true")
        pdf_form_separate = self.get("pdf_form_separate").lower() in ("1", "true")
        pdf_form_overwrite = self.get("pdf_form_overwrite")

        # try to get form pdf file
        form = None
        if self.files:
            form, = self.files
            if form.abspath and os.path.isfile(form.abspath):
                fields = tuple(_get_fields_from_from_and_node(form.abspath, node))
            else:
                form = None

        # get first document of content node
        for fnode in node.files:
            if fnode.filetype == "document":
                break
        else:
            fnode = None

        if not form or not (pdf_form_separate or fnode):
            logg.warning("workflowstep %s (%s): could not process pdf form - node: '%s' (%s)",
                         self.name, self.id, node.name, node.id)
            self.forward(node, True)
            return

        pages = fillPDFForm(form.abspath, fields, pdf_fields_editable)
        if pages is None:  # error in pdf creation -> forward to false operation
            logg.error("workflowstep %s (%s): could not create pdf file - node: '%s' (%s)",
                       self.name, self.id, node.name, node.id)
            self.forward(node, False)
            return

        if not pdf_form_separate:
            origname = fnode.abspath
            outfile = addPagesToPDF(pages, origname)
            for f in node.files:
                node.files.remove(f)
            fnode.path = outfile.replace(config.get("paths.datadir"), "")
            node.files.append(fnode)
            node.files.append(File(origname, 'upload', 'application/pdf'))  # store original filename
            node.event_files_changed()
            db.session.commit()
            logg.info("workflowstep '%s' (%s): added pdf form to pdf (node '%s' (%s)) fields: %s",
                      self.name, self.id, node.name, node.id, fields)
            self.forward(node, True)
            return

        importdir = getImportDir()
        try:
            # Build the filename of the form file on disk.
            # Note that the filename is underscore separated
            # and the part after the last underscore is
            # visible to the user when the file gets
            # emailed in ``email.py``.
            new_form_path = [str(node.id), form.base_name]
            if pdf_form_overwrite:
                new_form_path.insert(1, _utils_utils.gen_secure_token(128))
            new_form_path = join_paths(importdir, "_".join(new_form_path))
            # copy new file and remove tmp
            shutil.copy(pages, new_form_path)
            os.remove(pages)
        except:
            logg.exception("workflowstep %s (%s): could not copy pdf form to import directory - node: '%s' (%s), import directory: '%s'",
                           self.name, self.id, node.name, node.id, importdir)
        node.files.append(File(new_form_path, 'wfstep-addformpage', 'application/pdf'))
        db.session.commit()
        logg.info("workflowstep '%s' (%s): added separate pdf form to node (node '%s' (%s)) fields: %s, path: '%s'",
                  self.name, self.id, node.name, node.id, fields, new_form_path)
        self.forward(node, True)

    def show_workflow_node(self, node, req):
        self.forward(node, True)

    def admin_settings_get_html_form(self, req):
        pdfs = tuple(f for f in self.files if f.filetype=="wfstep-addformpage")
        if len(pdfs) == 1:
            context = dict(
                    filebasename=pdfs[0].base_name,
                    filesize=pdfs[0].size,
                    fileurl=u'/file/{}/{}'.format(self.id, pdfs[0].base_name),
                   )
        else:
            context = dict(filebasename=None, filesize=None, fileurl=None)
        context.update(dict(
                fields_editable=self.get('pdf_fields_editable'),
                form_separate=self.get('pdf_form_separate'),
                form_overwrite=self.get('pdf_form_overwrite'),
               ))

        return _tal.processTAL(
            context,
            file="workflow/addformpage.html",
            macro="workflow_step_type_config",
            request=req,
           )

    def admin_settings_save_form_data(self, data):
        data = data.to_dict()
        pdfform = data.pop('pdfform', None)
        if pdfform:
            for f in self.files:
                self.files.remove(f)
            self.files.append(_fileutils.importFile(_fileutils.sanitize_filename(pdfform.filename), pdfform,
                                              filetype="wfstep-addformpage"))
        for attr in ('fields_editable', 'form_separate', 'form_overwrite'):
            self.set("pdf_{}".format(attr), "1" if data.pop(attr, None) else "")
        assert not data
        db.session.commit()

    @staticmethod
    def getLabels():
        return {"de":
                [
                    ("workflowstep-addformpage", u"PDF-Seiten hinzufügen"),
                    ("workflowstep-addformpage_label_current_pdfform", "Aktuelles Formular:"),
                    ("workflowstep-addformpage_label_replace_pdfform", "Eine PDF-Form hier ersetzen"),
                    ("workflowstep-addformpage_label_upload_pdfform", "Eine PDF-Form hier hochladen"),
                    ("workflowstep-addformpage_label_fields_editable", "PDF-Form-Felder editierbar"),
                    ("workflowstep-addformpage_label_form_separate", u"PDF-Form separat an Knoten anhängen"),
                    ("workflowstep-addformpage_label_overwrite", u"PDF-Form überschreiben"),
                ],
                "en":
                [
                    ("workflowstep-addformpage", "add PDF pages"),
                    ("workflowstep-addformpage_label_current_pdfform", "Current PDF form:"),
                    ("workflowstep-addformpage_label_replace_pdfform", "Replace one PDF form here"),
                    ("workflowstep-addformpage_label_fields_editable", "PDF form fields editable"),
                    ("workflowstep-addformpage_label_form_separate", "append PDF form separately to node"),
                    ("workflowstep-addformpage_label_overwrite", "Overwrite existing form"),
                ]
                }
