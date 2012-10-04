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
import os.path
import logging

from workflow import WorkflowStep, getNodeWorkflow, getNodeWorkflowStep
from core.translation import t
from metadata.upload import getFilelist

import utils.utils as utils
import core.tree as tree
import core.config as config

logger = logging.getLogger("backend")


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
            key, value = line.split(':')
            key = key.strip()
            d[key] = value.strip()
    field_dicts.append(d)
    return field_dicts


def fillPDFForm(formPdf, fields, outputPdf="filled.pdf", input_is_fullpath=False, editable=False):
    """
        fill given pdf file with form fields with given attributes and store result in pdf file
    """
    # build data file
    try:
        res = '%FDF-1.2\n%\xe2\xe3\xcf\xd3\r\n1 0 obj\n<</FDF<</Fields['
        for field in fields:
            res += '<</T('+field[0]+')/V('+field[1]+')>>\n'
        res += ']>>/Type/Catalog>>\nendobj\ntrailer\r\n<</Root 1 0 R>>\r\n%%EOF\r\n'

        fout = open(config.get('paths.tempdir')+'infdata.fdf', 'wb')
        fout.write(res)
        fout.close()

        if not input_is_fullpath:
            formPdf = config.get('plugins.tum') + 'inf/'+formPdf

        # fill data in form pdf and generate pdf
        if editable:
            os.system('pdftk %s fill_form %sinfdata.fdf output %s%s' %(formPdf, config.get('paths.tempdir'), config.get('paths.tempdir'), outputPdf))
        else:
            os.system('pdftk %s fill_form %sinfdata.fdf output %s%s flatten' %(formPdf, config.get('paths.tempdir'), config.get('paths.tempdir'), outputPdf))

    except Exception, e:
        logger.error("error while filling pdf form: " + str(e))
    return config.get('paths.tempdir')+outputPdf


def addPagesToPDF(prefile, pdffile):
    outfile = pdffile[:-4]+"1.pdf"
    try:
        os.system("pdftk %s %s output %s" %(prefile, pdffile, outfile))
        os.remove(prefile)
    except Exception, e:
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
            if len(authors)>1:
                authors = ", ".join(authors[:-1]) + " and "+authors[-1]
            else:
                authors = authors[0]
            return authors

        # get pdf form appended to this workflow step through upload field 'upload_pdfform'
        current_workflow = getNodeWorkflow(node)
        current_workflow_step = getNodeWorkflowStep(node)
        formfilelist, formfilelist2 = getFilelist(current_workflow_step, 'upload_pdfform')

        pdf_fields_editable = current_workflow_step.get("pdf_fields_editable")
        
        if pdf_fields_editable.lower() in ["1", "true"]:
            pdf_fields_editable = True
        else:
            pdf_fields_editable = False

        fields = []
        f_retrieve_path = None

        if formfilelist:
            # take newest (mtime)
            f_mtime, f_name, f_mimetype, f_size, f_type, f_retrieve_path, f = formfilelist[-1]

            pdftk_fields_dump = get_pdftk_fields_dump(f_retrieve_path)

            for field_dict in parse_pdftk_fields_dump(pdftk_fields_dump):
                fieldname = field_dict.get('FieldName', None)
                if fieldname:
                    value = ''
                    if fieldname in dict(node.items()):
                        value = node.get(fieldname)
                        if fieldname.find('author') >= 0:
                            value = reformatAuthors(value)
                    else:
                        msg = "workflowstep %s (%s): could not find attribute for pdf form field '%s' - node: '%s' (%s)" % (current_workflow_step.name, str(current_workflow_step.id), fieldname, node.name, node.id)
                        logger.warning(msg)
                    value = utils.utf82iso(value)
                    fields.append((fieldname, value))


        if fnode and f_retrieve_path and os.path.isfile(f_retrieve_path):
            pages = fillPDFForm(f_retrieve_path, fields, input_is_fullpath=True, editable=pdf_fields_editable)
            origname = fnode.retrieveFile()
            outfile = addPagesToPDF(pages, origname)

            for f in node.getFiles():
                node.removeFile(f)
            fnode._path = outfile.replace(config.get("paths.datadir"),"")
            node.addFile(fnode)
            node.addFile(tree.FileNode(origname, 'upload', 'application/pdf')) # store original filename
            node.event_files_changed()

            logger.info("workflow '%s' (%s), workflowstep '%s' (%s): added pdf form to pdf (node '%s' (%s)) fields: %s" % (current_workflow.name, str(current_workflow.id), current_workflow_step.name, str(current_workflow_step.id), node.name, node.id, str(fields)))

        else:
            logger.warning("workflowstep %s (%s): could not process pdf form - node: '%s' (%s)" % (current_workflow_step.name, str(current_workflow_step.id), node.name, node.id))

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
        return ret

    def getLabels(self):
        return { "de":
            [
                ("workflowstep-addformpage", "PDF-Seiten hinzuf\xc3\xbcgen"),
                ("workflowstep-addformpage_label_upload_pdfform", "Eine PDF-Form hier hochladen"),
                ("workflowstep-addformpage_label_pdf_fields_editable", "PDF-Form-Felder editierbar"),
            ],
           "en":
            [
                ("workflowstep-addformpage", "add PDF pages"),
                ("workflowstep-addformpage_label_upload_pdfform", "Upload one PDF form here"),
                ("workflowstep-addformpage_label_pdf_fields_editable", "PDF form fields editable"),
            ]
            }
