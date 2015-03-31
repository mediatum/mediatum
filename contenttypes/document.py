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
import core.acl as acl
import os
import codecs
from utils.utils import splitfilename, u, OperationException, utf8_decode_escape
from schema.schema import VIEW_HIDE_EMPTY
from core.translation import lang, t
from core.acl import AccessData
from core.styles import getContentStyles
from lib.pdf import parsepdf
from core.attachment import filebrowser
from contenttypes.data import Content
from core.transition.postgres import check_type_arg_with_schema
from core.file import File
from core import db

logg = logging.getLogger(__name__)


@check_type_arg_with_schema
class Document(Content):

    @classmethod
    def getTypeAlias(cls):
        return "document"

    @classmethod
    def getOriginalTypeName(cls):
        return "document"

    @classmethod
    def getCategoryName(cls):
        return "document"

    def _prepareData(self, req, words=""):
        access = acl.AccessData(req)
        mask = self.getFullView(lang(req))
        obj = {'deleted': False, 'access': access}
        node = self
        if self.get('deleted') == 'true':
            node = self.getActiveVersion()
            obj['deleted'] = True
        if mask:
            obj['metadata'] = mask.getViewHTML([node], VIEW_HIDE_EMPTY, lang(req), mask=mask)  # hide empty elements
        else:
            obj['metadata'] = []
        obj['node'] = node
        obj['path'] = req and req.params.get("path", "") or ""
        files, sum_size = filebrowser(node, req)

        obj['attachment'] = files
        obj['sum_size'] = sum_size

        obj['bibtex'] = False
        if node.getMask("bibtex"):
            obj['bibtex'] = True

        if node.has_object():
            obj['canseeoriginal'] = access.hasAccess(node, "data")
            if node.get('system.origname') == "1":
                obj['documentlink'] = u'/doc/{}/{}'.format(node.id, node.name)
                obj['documentdownload'] = u'/download/{}/{}'.format(node.id, node.name)
            else:
                obj['documentlink'] = u'/doc/{}/{}.pdf'.format(node.id, node.id)
                obj['documentdownload'] = u'/download/{}/{}.pdf'.format(node.id, node.id)
        else:
            obj['canseeoriginal'] = False
        obj['documentthumb'] = u'/thumb2/{}'.format(node.id)
        if "oogle" not in (req.get_header("user-agent") or ""):
            obj['print_url'] = u'/print/{}'.format(node.id)
        else:
            # don't confuse search engines with the PDF link
            obj['print_url'] = None
            obj['documentdownload'] = None
        if "style" in req.params.keys():
            req.session["full_style"] = req.params.get("style", "full_standard")
        elif "full_style" not in req.session.keys():
            if "contentarea" in req.session.keys():
                col = req.session["contentarea"].collection
                req.session["full_style"] = col.get("style_full")
            else:
                req.session["full_style"] = "full_standard"

        obj['style'] = req.session["full_style"]
        return obj

    """ format big view with standard template """
    def show_node_big(self, req, template="", macro=""):
        if template == "":
            styles = getContentStyles("bigview", contenttype=self.getContentType())
            if len(styles) >= 1:
                template = styles[0].getTemplate()
        return req.getTAL(template, self._prepareData(req), macro)

    def isContainer(self):
        return 0

    def has_object(self):
        for f in self.files:
            if f.type == "doc" or f.type == "document":
                return True
        return False

    def getLabel(self):
        return self.name

    def getSysFiles(self):
        return ["doc", "document", "thumb", "thumb2", "presentati", "presentation", "fulltext", "fileinfo"]

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
            elif f.type == "doc":
                doc = f
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

        db.session.commit()

        if doc:
            path, ext = splitfilename(doc.abspath)

            if not (thumb and present and fulltext and fileinfo):
                thumbname = path + ".thumb"
                thumb2name = path + ".thumb2"
                fulltextname = path + ".txt"
                infoname = path + ".info"
                tempdir = config.get("paths.tempdir")

                try:
                    pdfdata = parsepdf.parsePDF2(doc.abspath, tempdir)
                except parsepdf.PDFException as ex:
                    raise OperationException(ex.value)
                with codecs.open(infoname, "rb", encoding='utf8') as fi:
                    for line in fi.readlines():
                        i = line.find(':')
                        if i > 0:
                            self.set("pdf_" + line[0:i].strip().lower(), utf8_decode_escape(line[i + 1:].strip()))

                self.files.append(File(thumbname, "thumb", "image/jpeg"))
                self.files.append(File(thumb2name, "presentation", "image/jpeg"))
                self.files.append(File(fulltextname, "fulltext", "text/plain"))
                self.files.append(File(infoname, "fileinfo", "text/plain"))

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
        access = AccessData(req)
        if not access.hasAccess(self, "data") or not access.hasAccess(self, "read"):
            req.write(t(req, "permission_denied"))
            return

        for f in self.files:
            if f.filetype == "doc" or f.filetype == "document":
                req.sendFile(f.abspath, f.mimetype)
                return

    def popup_thumbbig(self, req):
        self.popup_fullsize(req)

    def getEditMenuTabs(self):
        return "menulayout(view);menumetadata(metadata;files;admin;lza);menuclasses(classes);menusecurity(acls)"

    def getDefaultEditTab(self):
        return "view"

    def processDocument(self, dest):
        for file in self.files:
            if file.getType() == "document":
                filename = file.abspath
                if os.sep == '/':
                    cmd = "cp %s %s" % (filename, dest)
                    ret = os.system(cmd)
                else:
                    cmd = "copy %s %s" % (filename, dest + self.id + ".pdf")
                    ret = os.system(cmd.replace('/', '\\'))
        return 1
