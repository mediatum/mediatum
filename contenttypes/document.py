# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import logging

import core.config as config
import os
import shutil
import codecs
import core.httpstatus as _httpstatus
import core.translation as _core_translation
from utils.utils import splitfilename, u, OperationException, utf8_decode_escape
from utils.search import import_node_fulltext
from web.frontend.filehelpers import version_id_from_req
from schema.schema import VIEW_HIDE_EMPTY, Metafield
from lib.pdf import parsepdf
from core.attachment import filebrowser
from contenttypes.data import Content, prepare_node_data
from core.postgres import check_type_arg_with_schema
from core import File
from core import db
from core.request_handler import sendFile as _sendFile
from contenttypes.data import BadFile as _BadFile

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

    obj['data_access'] = node.has_data_access()
    obj['has_original'] = node.has_object()

    if obj['has_original']:
        if node.system_attrs.get('origname') == "1":
            obj['documentlink'] = u'/doc/{}/{}'.format(node.id, node.name)
            obj['documentdownload'] = u'/download/{}/{}'.format(node.id, node.name)
        else:
            obj['documentlink'] = u'/doc/{}/{}.pdf'.format(node.id, node.id)
            obj['documentdownload'] = u'/download/{}/{}.pdf'.format(node.id, node.id)

            if not node.isActiveVersion():
                version_id = unicode(version_id_from_req(req.args))
                obj['documentlink'] += "?v=" + version_id
                obj['documentdownload'] += "?v=" + version_id

    obj['documentthumb'] = u'/thumb2/{}'.format(node.id)
    if not node.isActiveVersion():
        version_id = unicode(version_id_from_req(req.args))
        obj['documentthumb'] += "?v=" + version_id
        obj['tag'] = version_id

    # XXX: do we really need this spider filtering?
    user_agent = req.user_agent.string or ""
    is_spider = "oogle" in user_agent or "aidu" in user_agent
    
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

    def _prepareData(self, req, words=""):
        return _prepare_document_data(self, req)

    @property
    def document(self):
        # XXX: this should be one() instead of first(), but we must enforce this unique constraint in the DB first
        return self.files.filter_by(filetype=u"document").first()

    def has_object(self):
        return bool(self.document)

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
                    pdfdata = parsepdf.parsePDF(doc.abspath, tempdir)
                except parsepdf.PDFException as ex:
                    if ex.value == 'error:document encrypted':
                        # allow upload of encrypted document
                        db.session.commit()
                        return
                    raise OperationException(ex.value)
                except Exception as exc:
                    if str(exc)=="DecompressionBombError":  # must match error string in parsepdf.py
                        raise _BadFile("image_too_big")
                    raise
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

        if doc:
            import_node_fulltext(self, overwrite=True)

        db.session.commit()

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
            req.response.set_data(_core_translation.t(req, "permission_denied"))
            req.response.status_code = _httpstatus.HTTP_FORBIDDEN
            return

        document = self.document

        if document is not None:
            _sendFile(req, document.abspath, document.mimetype)

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

    def metaFields(self, lang=None):
        metafields = []

        field = Metafield(u"nodename", attrs={
            "label": _core_translation.t(lang, "node name"),
            "type": u"text"
        })
        metafields.append(field)
        return metafields
