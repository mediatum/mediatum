# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import codecs
import logging
import os
import re as _re
import shutil
import subprocess as _subprocess

import PIL.Image as _PIL_Image

import core as _core
import contenttypes.data as _contenttypes_data
import utils.process as _utils_process
import utils.utils as _utils_utils
from core.database.postgres.file import File
from core.attachment import filebrowser
from core.postgres import check_type_arg_with_schema
from schema.schema import Metafield
from utils.search import import_node_fulltext
from web.frontend.filehelpers import version_id_from_req

logg = logging.getLogger(__name__)

class _PdfEncryptedError(Exception):
    pass

_pdfinfo_attribute_names = frozenset((
        "Title",
        "Subject",
        "Keywords",
        "Author",
        "Creator",
        "Producer",
        "CreationDate",
        "ModDate",
        "Tagged",
        "Pages",
        "Encrypted",
        "Page size",
        "File size",
        "Optimized",
        "PDF Version",
        "Metadata",
    ))
_re_pagesize = _re.compile(r"^([.\d]+) x ([.\d]+) pts.*$").match


def _pdfinfo(filename):
    # process info file
    try:
        out = _utils_process.check_output(("pdfinfo", filename))
    except _subprocess.CalledProcessError:
        logg.exception("failed to extract metadata from file %s")
        return {}
    data = {}
    for line in out.splitlines():
        for attr in _pdfinfo_attribute_names:
            parts = line.replace("\n", "").replace("\r", "").split(attr + ":")
            # subtype line is indented and is ignored
            if len(parts) != 2 or parts[0]:
                continue
            # pdfinfo cannot handle strings in utf-16, they are clipped after BOM_UTF16_BE:
            if parts[1].strip() == codecs.BOM_UTF16_BE:
                break
            data[attr] = parts[1].strip()

            if attr == "Encrypted" and parts[1].strip().startswith("yes"):
                for s_option in parts[1].strip()[5:-1].split(" "):
                    option = s_option.split(":")
                    if option[1] == "":
                        break
                    data[option[0]] = option[1]
                data[attr] = "yes"
            break
    return {k:_utils_utils.utf8_decode_escape(v.strip()) for k,v in data.iteritems()}


def _process_pdf(filename, thumbnailname, fulltextname):
    name = ".".join(filename.split(".")[:-1])
    fulltext_from_pdftotext = name + ".pdftotext"  # output of pdf to text, possibly not normalized utf-8

    pdfinfo = _pdfinfo(filename)
    # test for correct rights
    if pdfinfo.get("Encrypted") == "yes":
        raise _PdfEncryptedError("error:document encrypted")

    size = map(float, _re_pagesize(pdfinfo["Page size"]).groups())
    size = _contenttypes_data.get_thumbnail_size(*size)
    # generate thumbnail
    try:
        _utils_process.check_call((
            "pdftoppm",
            "-singlefile",
            "-jpeg",
            "-jpegopt", "progressive=y,optimize=y",
            "-scale-to-x", str(size[0]),
            "-scale-to-y", str(size[1]),
            filename,
            u"{}.pdftoppm-temp".format(thumbnailname),
        ))
        os.rename(u"{}.pdftoppm-temp.jpg".format(thumbnailname), thumbnailname)
    except _subprocess.CalledProcessError:
        logg.exception("failed to create PDF thumbnail for file " + filename)
    finally:
        with _utils_utils.suppress(OSError, warn=False):
            os.remove(u"{}.pdftoppm-temp.jpg".format(thumbnailname))

    # extract fulltext (xpdf)
    try:
        _utils_process.check_call(("pdftotext", "-enc", "UTF-8", filename, fulltext_from_pdftotext))
    except _subprocess.CalledProcessError:
        logg.exception("failed to extract fulltext from file %s", filename)

    # normalization of fulltext (uconv)
    try:
        _utils_process.check_call((
            "uconv",
            "-x", "any-nfc",
            "-f", "UTF-8",
            "-t", "UTF-8",
            "--output",
            fulltextname,
            fulltext_from_pdftotext,
        ))
    except _subprocess.CalledProcessError:
        logg.exception("failed to normalize fulltext from file %s", filename)

    with _utils_utils.suppress(OSError, warn=False):
        os.remove(fulltext_from_pdftotext)

    return pdfinfo


def _prepare_document_data(node, req, words=""):
    obj = _contenttypes_data.prepare_node_data(node, req)
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
    obj['version'] = req.args.get("v", "")
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

    obj['documentthumb'] = u'/thumbnail/{}'.format(node.id)
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
class Document(_contenttypes_data.Content):

    @classmethod
    def get_original_filetype(cls):
        return "document"

    @classmethod
    def get_sys_filetypes(cls):
        return [u"document", u"fulltext", u"thumbnail"]

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

        thumbnail = 0
        fulltext = 0
        doc = None
        for f in self.files:
            if f.type == "thumbnail":
                thumbnail = 1
            elif f.type == "fulltext":
                fulltext = 1
            elif f.type == "document":
                doc = f
        if not doc:
            for f in self.files:
                if f.type == "thumbnail":
                    self.files.remove(f)
                elif f.type == "fulltext":
                    self.files.remove(f)

            _core.db.session.commit()
            return

        if thumbnail or fulltext:
            return

        path, ext = _utils_utils.splitfilename(doc.abspath)
        thumbnailname = u"{}.thumbnail.jpeg".format(path)
        fulltextname = u"{}.txt".format(path)
        try:
            pdfinfo = _process_pdf(doc.abspath, thumbnailname, fulltextname)
        except _PdfEncryptedError:
            # allow upload of encrypted document
            _core.db.session.commit()
            return
        except _PIL_Image.DecompressionBombError:
            # must match error string in parsepdf.py
            raise _contenttypes_data.BadFile("image_too_big")
        else:
            unwanted_attrs = self.get_unwanted_exif_attributes()
            for key, value in pdfinfo.iteritems():
                key = key.lower()
                if key not in unwanted_attrs:
                    self.set(u"pdf_{}".format(key), value)

        self.files.append(File(thumbnailname, "thumbnail", "image/jpeg"))
        self.files.append(File(fulltextname, "fulltext", "text/plain"))

        import_node_fulltext(self, overwrite=True)

        _core.db.session.commit()


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

        field = Metafield(u"nodename")
        field.set("label", "node name")
        field.setFieldtype("text")
        metafields.append(field)
        return metafields
