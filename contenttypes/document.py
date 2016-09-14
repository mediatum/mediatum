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
import logging

import core.config as config
import os
import shutil
import codecs
from utils.utils import splitfilename, u, OperationException, utf8_decode_escape
from utils.search import import_node_fulltext
from schema.schema import VIEW_HIDE_EMPTY
from core.translation import lang, t
from lib.pdf import parsepdf
from core.attachment import filebrowser
from contenttypes.data import Content, prepare_node_data
from core.transition.postgres import check_type_arg_with_schema
from core import File
from core import db

logg = logging.getLogger(__name__)


def _prepare_document_data(node, req, words=""):
    obj = prepare_node_data(node, req)
    if obj["deleted"]:
        # no more processing needed if this object version has been deleted
        # rendering has been delegated to current version
        return obj

    files, sum_size = filebrowser(node, req)

    obj['attachment'] = files
    obj['sum_size'] = sum_size
    obj['bibtex'] = False

    if node.getMask(u"bibtex"):
        obj['bibtex'] = True

    if node.has_object():
        obj['canseeoriginal'] = node.has_data_access()
        if node.system_attrs.get('origname') == "1":
            obj['documentlink'] = u'/doc/{}/{}'.format(node.id, node.name)
            obj['documentdownload'] = u'/download/{}/{}'.format(node.id, node.name)
        else:
            obj['documentlink'] = u'/doc/{}/{}.pdf'.format(node.id, node.id)
            obj['documentdownload'] = u'/download/{}/{}.pdf'.format(node.id, node.id)

            if not node.isActiveVersion():
                obj['documentlink'] += "?v=" + node.tag
                obj['documentdownload'] += "?v=" + node.tag

    else:
        obj['canseeoriginal'] = False

    obj['documentthumb'] = u'/thumb2/{}'.format(node.id)
    if not node.isActiveVersion():
        obj['documentthumb'] += "?v=" + node.tag
        obj['tag'] = node.tag

    # XXX: do we really need this spider filtering?
    user_agent = req.get_header("user-agent") or ""
    is_spider = "oogle" in user_agent or "aidu" in user_agent
    
    obj['print_url'] = None

    if config.getboolean("config.enable_printing") and not is_spider:
        obj['print_url'] = u'/print/{}'.format(node.id)
    
    if is_spider:
        # don't confuse search engines with the PDF link
        obj['documentdownload'] = None

    full_style = req.args.get("style", "full_standard")
    if full_style:
        obj['style'] = full_style

    return obj


@check_type_arg_with_schema
class Document(Content):

    @classmethod
    def get_original_filetype(cls):
        return "document"

    @classmethod
    def get_sys_filetypes(cls):
        return [u"document", u"thumb", u"thumb2", u"presentation", u"fulltext", u"fileinfo"]

    @classmethod
    def get_default_edit_menu_tabs(cls):
        return "menulayout(view);menumetadata(metadata;files;admin;lza);menuclasses(classes);menusecurity(acls)"

    def _prepareData(self, req, words=""):
        return _prepare_document_data(self, req)

    @property
    def document(self):
        # XXX: this should be one() instead of first(), but we must enforce this unique constraint in the DB first
        return self.files.filter_by(filetype=u"document").first()

    def has_object(self):
        return self.document is not None

    """ postprocess method for object type 'document'. called after object creation """
    def event_files_changed(self):
        logg.debug("Postprocessing node %s", self.id)

        thumb = 0
        fulltext = 0
        doc = None
        present = 0
        fileinfo = 0
        for f in self.files:
            if f.type == "thumb":
                thumb = 1
            elif f.type.startswith("present"):
                present = 1
            elif f.type == "fulltext":
                fulltext = 1
            elif f.type == "fileinfo":
                fileinfo = 1
            elif f.type == "document":
                doc = f
        if not doc:
            for f in self.files:
                if f.type == "thumb":
                    self.files.remove(f)
                elif f.type.startswith("present"):
                    self.files.remove(f)
                elif f.type == "fileinfo":
                    self.files.remove(f)
                elif f.type == "fulltext":
                    self.files.remove(f)

        #fetch unwanted tags to be omitted
        unwanted_attrs = self.get_unwanted_exif_attributes()

        if doc:
            path, ext = splitfilename(doc.abspath)

            if not (thumb and present and fulltext and fileinfo):
                thumbname = path + ".thumb"
                thumb2name = path + ".thumb2"
                fulltextname = path + ".txt"
                infoname = path + ".info"
                tempdir = config.get("paths.tempdir")

                try:
                    pdfdata = parsepdf.parsePDFExternal(doc.abspath, tempdir)
                except parsepdf.PDFException as ex:
                    raise OperationException(ex.value)
                with codecs.open(infoname, "rb", encoding='utf8') as fi:
                    for line in fi.readlines():
                        i = line.find(':')
                        if i > 0:
                            if any(tag in line[0:i].strip().lower() for tag in unwanted_attrs):
                                continue
                            self.set("pdf_" + line[0:i].strip().lower(), utf8_decode_escape(line[i + 1:].strip()))

                self.files.append(File(thumbname, "thumb", "image/jpeg"))
                self.files.append(File(thumb2name, "presentation", "image/jpeg"))
                self.files.append(File(fulltextname, "fulltext", "text/plain"))
                self.files.append(File(infoname, "fileinfo", "text/plain"))

        db.session.commit()

        if doc:
            import_node_fulltext(self, overwrite=True)

    def get_unwanted_exif_attributes(self):
            '''
            Returns a list of unwanted attributes which are not to be extracted from uploaded documents
            @return: list
            '''
            return ['creator',
                    'producer']

    """ list with technical attributes for type document """
    def getTechnAttributes(self):
        return {"PDF": {"pdf_moddate": "Datum",
                        "pdf_file size": "Dateigr&ouml;&szlig;e",
                        "pdf_title": "Titel",
                        "pdf_creationdate": "Erstelldatum",
                        "pdf_author": "Autor",
                        "pdf_pages": "Seitenzahl",
                        "pdf_producer": "Programm",
                        "pdf_pagesize": "Seitengr&ouml;&szlig;e",
                        "pdf_creator": "PDF-Erzeugung",
                        "pdf_encrypted": "Verschl&uuml;sselt",
                        "pdf_tagged": "Tagged",
                        "pdf_optimized": "Optimiert",
                        "pdf_linearized": "Linearisiert",
                        "pdf_version": "PDF-Version"},

                "Common": {"pdf_print": "druckbar",
                           "pdf_copy": "Inhalt entnehmbar",
                           "pdf_change": "&auml;nderbar",
                           "pdf_addnotes": "kommentierbar"},
                "Standard": {"creationtime": "Erstelldatum",
                             "creator": "Ersteller"}}

    """ popup window for actual nodetype """
    def popup_fullsize(self, req):
        if not self.has_data_access() or not self.has_read_access():
            req.write(t(req, "permission_denied"))
            return

        document = self.document

        if document is not None:
            req.sendFile(document.abspath, document.mimetype)

    def popup_thumbbig(self, req):
        self.popup_fullsize(req)

    def processDocument(self, dest):
        for file in self.files:
            if file.filetype == "document":
                filename = file.abspath
                try:
                    shutil.copy(filename, dest)
                except:
                    logg.exception("while copying file")
        return 1
