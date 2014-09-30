"""
 mediatum - a multimedia content repository

 Copyright (C) 2011 Arne Seifert <arne.seifert@tum.de>

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
import re
import os.path
import shutil
import logging
import codecs

from .workflow import WorkflowStep, getNodeWorkflow, getNodeWorkflowStep, registerStep
from core.translation import t, addLabels
from metadata.upload import getFilelist
from schema.schema import getMetaType
from utils.fileutils import getImportDir
from utils.utils import join_paths
from utils.date import format_date, now

import utils.utils as utils
import core.tree as tree
import core.config as config

logger = logging.getLogger("backend")


def register():
    tree.registerNodeClass("workflowstep-addformpage", WorkflowStep_AddFormPage)
    registerStep("workflowstep-addformpage")
    addLabels(WorkflowStep_AddFormPage.getLabels())


def get_pdftk_fields_dump(path_to_pdf):
    p = os.popen('pdftk %s dump_data_fields' % path_to_pdf)
    s = p.read()
    p.close()
    return s


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
            #key, value = line.split(':')
            d[vals[0].strip()] = ":".join(vals[1:]).strip()
    field_dicts.append(d)
    return field_dicts

TAG_RE = re.compile(r'<[^>]+>')


def remove_tags(text):
    return TAG_RE.sub('', text)


def smart_encode_str(s):
    """Create a UTF-16 encoded PDF string literal for `s`."""
    try:
        utf16 = s.encode('utf_16_be')
    except AttributeError:  # ints and floats
        utf16 = str(s).encode('utf_16_be')
    safe = utf16.replace(b'\x00)', b'\x00\\)').replace(b'\x00(', b'\x00\\(')
    return b''.join((codecs.BOM_UTF16_BE, safe))


def handle_hidden(key, fields_hidden):
    if key in fields_hidden:
        return b"/SetF 2"
    else:
        return b"/ClrF 2"


def handle_readonly(key, fields_readonly):
    if key in fields_readonly:
        return b"/SetFf 1"
    else:
        return b"/ClrFf 1"


def handle_data_strings(fdf_data_strings, fields_hidden, fields_readonly):
    for (key, value) in fdf_data_strings:
        if isinstance(value, bool) and value:
            value = b'/Yes'
        elif isinstance(value, bool) and not value:
            value = b'/Off'
        else:
            value = b''.join([b' (', smart_encode_str(value), b')'])
        yield b''.join([b'<<\n/V', value, b'\n/T (',
                        smart_encode_str(key), b')\n',
                        handle_hidden(key, fields_hidden), b'\n',
                        handle_readonly(key, fields_readonly), b'\n>>\n'])


def handle_data_names(fdf_data_names, fields_hidden, fields_readonly):
    for (key, value) in fdf_data_names:
        yield b''.join([b'<<\n/V /', smart_encode_str(value), b'\n/T (',
                        smart_encode_str(key), b')\n',
                        handle_hidden(key, fields_hidden), b'\n',
                        handle_readonly(key, fields_readonly), b'\n>>\n'])


def forge_fdf(pdf_form_url="", fdf_data_strings=[], fdf_data_names=[], fields_hidden=[], fields_readonly=[]):
    fdf = [b'%FDF-1.2\n%\xe2\xe3\xcf\xd3\r\n']
    fdf.append(b'1 0 obj\n<<\n/FDF\n')
    fdf.append(b'<<\n/Fields [\n')
    fdf.append(b''.join(handle_data_strings(fdf_data_strings, fields_hidden, fields_readonly)))
    fdf.append(b''.join(handle_data_names(fdf_data_names, fields_hidden, fields_readonly)))
    if pdf_form_url:
        fdf.append(b''.join(b'/F (', smart_encode_str(pdf_form_url), b')\n'))
    fdf.append(b']\n')
    fdf.append(b'>>\n')
    fdf.append(b'>>\nendobj\n')
    fdf.append(b'trailer\n\n<<\n/Root 1 0 R\n>>\n')
    fdf.append(b'%%EOF\n\x0a')
    return b''.join(fdf)


def fillPDFForm(formPdf, fields, outputPdf="filled.pdf", input_is_fullpath=False, editable=False):
    """
        fill given pdf file with form fields with given attributes and store result in pdf file
    """
    # build data file
    try:
        with open(config.get('paths.tempdir') + 'infdata.fdf', 'wb') as fdf_file:
            fdf_file.write(forge_fdf(fdf_data_strings=fields))

        #res = '%FDF-1.2\n%\xe2\xe3\xcf\xd3\r\n1 0 obj\n<</FDF<</Fields['
        # for field in fields:
        #    res += '<</T('+field[0]+')/V('+field[1]+')>>\n'
        #res += ']>>/Type/Catalog>>\nendobj\ntrailer\r\n<</Root 1 0 R>>\r\n%%EOF\r\n'

        #fout = open(config.get('paths.tempdir')+'infdata.fdf', 'wb')
        # fout.write(res)
        # fout.close()

        # fill data in form pdf and generate pdf
        if editable:
            os.system('pdftk %s fill_form %sinfdata.fdf output %s%s' %
                      (formPdf, config.get('paths.tempdir'), config.get('paths.tempdir'), outputPdf))
        else:
            os.system('pdftk %s fill_form %sinfdata.fdf output %s%s flatten' %
                      (formPdf, config.get('paths.tempdir'), config.get('paths.tempdir'), outputPdf))

    except Exception as e:
        logger.error("error while filling pdf form: " + str(e))
    return config.get('paths.tempdir') + outputPdf


def addPagesToPDF(prefile, pdffile):
    outfile = pdffile[:-4] + "1.pdf"
    try:
        os.system("pdftk %s %s output %s" % (prefile, pdffile, outfile))
        os.remove(prefile)
    except Exception as e:
        logger.error("error while adding pages: " + str(e))
    return outfile


class WorkflowStep_AddFormPage(WorkflowStep):

    """
        update given pdf-file and add some pre-pages
        pre-pages can use formular fields
    """

    def runAction(self, node, op=""):
        fnode = None
        for fnode in node.getFiles():
            if fnode.type == "document":
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

        schema = getMetaType(node.getSchema())

        if formfilelist:
            # take newest (mtime)
            f_mtime, f_name, f_mimetype, f_size, f_type, f_retrieve_path, f = formfilelist[-1]

            for field_dict in parse_pdftk_fields_dump(get_pdftk_fields_dump(f_retrieve_path)):
                fieldname = field_dict.get('FieldName', None)
                if fieldname:
                    value = ''
                    if fieldname in dict(node.items()):
                        schemafield = schema.getMetaField(fieldname)
                        value = schemafield.getFormatedValue(node)[1]
                        #value = node.get(fieldname)
                        if fieldname.find('author') >= 0:
                            value = reformatAuthors(value)
                    elif fieldname.lower() == 'node.schema':
                        value = getMetaType(node.getSchema()).getLongName()
                    elif fieldname.lower() == 'node.id':
                        value = str(node.id)
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
                                    v = node.id
                                elif m.group(0) == 'type':
                                    v = node.type
                                elif m.group(0) == 'schema':
                                    v = node.getMetaType(node.getSchema()).getLongName()
                                else:
                                    schemafield = schema.getMetaField(m.group(0))
                                    v = schemafield.getFormatedValue(node)[0]
                                    #v = node.get(m.group(0))
                                value = value.replace('[att:%s]' % (m.group(0)), v)
                    else:
                        logger.warning("workflowstep %s (%s): could not find attribute for pdf form field '%s' - node: '%s' (%s)" %
                                       (current_workflow_step.name, str(current_workflow_step.id), fieldname, node.name, node.id))
                    fields.append((fieldname, remove_tags(utils.desc(value)).decode("utf-8")))

        if not pdf_form_separate and fnode and f_retrieve_path and os.path.isfile(f_retrieve_path):
            pages = fillPDFForm(f_retrieve_path, fields, input_is_fullpath=True, editable=pdf_fields_editable)

            origname = fnode.retrieveFile()
            outfile = addPagesToPDF(pages, origname)

            for f in node.getFiles():
                node.removeFile(f)
            fnode._path = outfile.replace(config.get("paths.datadir"), "")
            node.addFile(fnode)
            node.addFile(tree.FileNode(origname, 'upload', 'application/pdf'))  # store original filename
            node.event_files_changed()
            logger.info(
                "workflow '%s' (%s), workflowstep '%s' (%s): added pdf form to pdf (node '%s' (%s)) fields: %s" %
                (current_workflow.name, str(
                    current_workflow.id), current_workflow_step.name, str(
                    current_workflow_step.id), node.name, node.id, str(fields)))
        elif pdf_form_separate and f_retrieve_path and os.path.isfile(f_retrieve_path):
            pages = fillPDFForm(f_retrieve_path, fields, input_is_fullpath=True, editable=pdf_fields_editable)
            importdir = getImportDir()
            try:
                new_form_path = join_paths(importdir, "%s_%s" % (node.id, f_name))
                counter = 0
                if not pdf_form_overwrite:  # build correct filename
                    while os.path.isfile(new_form_path):
                        counter += 1
                        new_form_path = join_paths(importdir, "%s_%s_%s" % (node.id, counter, f_name))
                shutil.copy(pages, new_form_path)
            except Exception as e:
                logger.error("workflowstep %s (%s): could not copy pdf form to import directory - node: '%s' (%s), import directory: '%s'" %
                             (current_workflow_step.name, str(current_workflow_step.id), node.name, node.id, importdir))
            found = 0
            for fn in node.getFiles():
                if fn.retrieveFile() == new_form_path:
                    found = 1
                    break
            if found == 0 or (found == 1 and not pdf_form_overwrite):
                node.addFile(tree.FileNode(new_form_path, 'pdf_form', 'application/pdf'))

            logger.info(
                "workflow '%s' (%s), workflowstep '%s' (%s): added separate pdf form to node (node '%s' (%s)) fields: %s, path: '%s'" %
                (current_workflow.name, str(
                    current_workflow.id), current_workflow_step.name, str(
                    current_workflow_step.id), node.name, node.id, str(fields), new_form_path))
        else:
            logger.warning("workflowstep %s (%s): could not process pdf form - node: '%s' (%s)" %
                           (current_workflow_step.name, str(current_workflow_step.id), node.name, node.id))

        self.forward(node, True)

    def show_workflow_node(self, node, req):
        self.forward(node, True)

    def metaFields(self, lang=None):
        ret = list()
        field = tree.Node("upload_pdfform", "metafield")
        field.set("label", t(lang, "workflowstep-addformpage_label_upload_pdfform"))
        field.set("type", "upload")
        ret.append(field)

        field = tree.Node("pdf_fields_editable", "metafield")
        field.set("label", t(lang, "workflowstep-addformpage_label_pdf_fields_editable"))
        field.set("type", "check")
        ret.append(field)

        field = tree.Node("pdf_form_separate", "metafield")
        field.set("label", t(lang, "workflowstep-addformpage_label_pdf_form_separate"))
        field.set("type", "check")
        ret.append(field)

        field = tree.Node("pdf_form_overwrite", "metafield")
        field.set("label", t(lang, "workflowstep-addformpage_label_pdf_overwrite"))
        field.set("type", "check")
        ret.append(field)
        return ret

    @staticmethod
    def getLabels():
        return {"de":
                [
                    ("workflowstep-addformpage", "PDF-Seiten hinzuf\xc3\xbcgen"),
                    ("workflowstep-addformpage_label_upload_pdfform", "Eine PDF-Form hier hochladen"),
                    ("workflowstep-addformpage_label_pdf_fields_editable", "PDF-Form-Felder editierbar"),
                    ("workflowstep-addformpage_label_pdf_form_separate", "PDF-Form separat an Knoten anh\xc3\xa4ngen"),
                    ("workflowstep-addformpage_label_pdf_overwrite", "PDF-Form \xc3\xbcberschreiben"),
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
