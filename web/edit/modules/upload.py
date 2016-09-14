# -*- coding: utf-8 -*-
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
import os
import codecs
import core.users as users

import re
import core.config as config
import zipfile
import random
import time
import logging

import json

from web.edit.edit_common import showdir, showoperations
from web.edit.edit import getTreeLabel
from utils.utils import join_paths, getMimeType, funcname, get_user_id, dec_entry_log
from utils.fileutils import importFileToRealname, importFileRandom
from schema.bibtex import importBibTeX, MissingMapping

from core.translation import translate, lang, addLabels
from core.translation import t as translation_t
from core import db
from contenttypes import Data
from core import Node
from schema.schema import Metadatatype, get_permitted_schemas, get_permitted_schemas_for_datatype
from sqlalchemy import func
from utils.compat import iteritems

logg = logging.getLogger(__name__)
identifier_importers = {}
q = db.query


class SortChoice:

    def __init__(self, label, value):
        self.label = label
        self.value = value


def getInformation():
    return {"version": "1.1", "system": 0}


def elemInList(list, name):
    for item in list:
        if item.__name__.lower() == name:
            return True
    return False


@dec_entry_log
def getDatatypes(req, schemes):
    dtypes = []
    datatypes = Data.get_all_datatypes()
    for scheme in schemes:
        for dtype in scheme.getDatatypes():
            if dtype not in dtypes:
                for t in datatypes:
                    if t.__name__.lower() == dtype and not elemInList(dtypes, t.__name__.lower()):
                        dtypes.append(t)
    dtypes.sort(lambda x, y: cmp(translate(x.__name__.lower(),
                                           request=req).lower(),
                                 translate(y.__name__.lower(),
                                           request=req).lower()))
    return dtypes


@dec_entry_log
def getContent(req, ids):

    user = users.getUserFromRequest(req)
    language = lang(req)

    if "action" in req.params:
        state = 'ok'

        if req.params.get('action') == "removefiles":
            basenode = q(Node).get(req.params.get('id'))
            for f in basenode.files:
                try:
                    os.remove(f.abspath)
                    pass
                except:
                    state = "error"
            basenode.files = []
            db.session.commit()
            req.write(json.dumps({'state': state}, ensure_ascii=False))
            return None

        if req.params.get('action') == "buildnode":  # create nodes
            basenode = q(Node).get(req.params.get('id'))
            newnodes = []
            errornodes = []
            basenodefiles_processed = []
            if req.params.get('uploader', '') == 'plupload':
                filename2scheme = {}
                for k in req.params:
                    if k.startswith("scheme_"):
                        filename2scheme[
                            k.replace('scheme_', '', 1)] = req.params.get(k)

                for f in basenode.files:
                    filename = f.name
                    if filename in filename2scheme:
                        mimetype = getMimeType(filename)

                        if mimetype[1] == "bibtex":  # bibtex import handler
                            try:
                                new_node = importBibTeX(f.abspath, basenode)
                                newnodes.append(new_node.id)
                                basenodefiles_processed.append(f)
                            except ValueError, e:
                                errornodes.append((filename, unicode(e)))

                        logg.debug("filename: %s, mimetype: %s", filename, mimetype)
                        logg.debug("__name__=%s, func=%s; _m=%s, _m[1]=%s", __name__, funcname(), mimetype, mimetype[1])

                        content_class = Node.get_class_for_typestring(mimetype[1])
                        node = content_class(name=filename, schema=filename2scheme[filename])

                        basenode.children.append(node)
                        node.set("creator", user.login_name)
                        node.set("creationtime",  unicode(time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(time.time()))))
                        # set filetype for uploaded file as requested by the content class
                        f.filetype = content_class.get_upload_filetype()
                        node.files.append(f)
                        node.event_files_changed()
                        newnodes.append(node.id)
                        basenodefiles_processed.append(f)
                        basenode.files.remove(f)
                        db.session.commit()
                        logg.info("%s created new node id=%s (name=%s, type=%s) by uploading file %s, "
                            "node is child of base node id=%s (name=%s, type=%s)", user.login_name, node.id, node.name, node.type,
                             filename, basenode.id, basenode.name, basenode.type)

            else:
                for filename in req.params.get('files').split('|'):
                    mimetype = getMimeType(filename)
                    logg.debug("... in %s.%s: getMimeType(filename=%s)=%s", __name__, funcname(), filename, mimetype)
                    if mimetype[1] == req.params.get('type') or req.params.get('type') == 'file':
                        for f in basenode.files:
                            # ambiguity here ?
                            if f.abspath.endswith(filename):
                                # bibtex import handler
                                if mimetype[1] == "bibtex" and not req.params.get('type') == 'file':
                                    try:
                                        new_node = importBibTeX(f.abspath, basenode)
                                        newnodes.append(new_node.id)
                                        basenodefiles_processed.append(f)
                                    except ValueError, e:
                                        errornodes.append((filename, unicode(e)))
                                    db.session.commit()
                                else:

                                    logg.debug("creating new node: filename: %s", filename)
                                    logg.debug("files at basenode: %s", [(x.getName(), x.abspath) for x in basenode.files])

                                    content_class = Node.get_class_for_typestring(req.params.get('type'))
                                    node = content_class(name=filename, schema=req.params.get('value'))

                                    basenode.children.append(node)
                                    node.set("creator", user.login_name)
                                    node.set("creationtime",  unicode(time.strftime('%Y-%m-%dT%H:%M:%S',
                                                                                    time.localtime(time.time()))))

                                    # clones to a file with random name
                                    cloned_file = importFileRandom(f.abspath)
                                    # set filetype for uploaded file as requested by the content class
                                    cloned_file.filetype = content_class.get_upload_filetype()
                                    node.files.append(cloned_file)
                                    node.event_files_changed()
                                    newnodes.append(node.id)
                                    basenodefiles_processed.append(f)

                                    logg.info("%s created new node id=%s (name=%s, type=%s) by uploading file %s, "
                                    "node is child of base node id=%s (name=%s, type=%s)", user.login_name, node.id, node.name, node.type, filename,
                                    basenode.id, basenode.name, basenode.type)

                                    break  # filename may not be unique

            new_tree_labels = [{'id': basenode.id, 'label': getTreeLabel(basenode, lang=language)}]
            for f in basenodefiles_processed:
                basenode.files.remove(f)
                f_path = f.abspath
                if os.path.exists(f_path):
                    logg.debug("%s going to remove file %s from disk", user.login_name, f_path)
                    os.remove(f_path)

            mime = getMimeType(filename)
            scheme_type = {mime[1]: []}
            for scheme in get_permitted_schemas():
                if mime[1] in scheme.getDatatypes():
                    scheme_type[mime[1]].append(scheme)
                    # break

            db.session.commit()
            # standard file
            content = req.getTAL('web/edit/modules/upload.html', {'files': [filename], 'schemes': scheme_type}, macro="uploadfileok")

            res = {'state': state, 'newnodes': newnodes, 'errornodes':
                              errornodes, 'new_tree_labels': new_tree_labels, 'ret': content}
            res = json.dumps(res, ensure_ascii=False)
            req.write(res)
            return None

        # add new object, only metadata
        if req.params.get('action') == "addmeta":
            schemes = get_permitted_schemas()
            dtypes = getDatatypes(req, schemes)
            if len(dtypes) == 1:  # load schemes for type
                schemes = get_permitted_schemas_for_datatype(dtypes[0].__name__.lower())
            content = req.getTAL('web/edit/modules/upload.html', {"datatypes": dtypes,
                                                                  "schemes": schemes,
                                                                  "language": lang(req),
                                                                  "identifier_importers": identifier_importers.values()},
                                 macro="addmeta")

            req.write(json.dumps({'content': content}, ensure_ascii=False))
            return None

        # deliver schemes for given contenttype
        if req.params.get('action') == 'getschemes':
            ret = []
            for scheme in get_permitted_schemas_for_datatype(req.params.get('contenttype')):
                ret.append({'id': scheme.name, 'name': scheme.getLongName()})
            req.write(json.dumps({'schemes': ret}, ensure_ascii=False))
            return None

        # create node with given type/schema
        if req.params.get('action') == "createobject":
            schema = req.params.get('schema')
            ctype = req.params.get('contenttype')

            node = Node(name=u"", type=ctype, schema=schema)
            basenode = q(Node).get(req.params.get('id'))
            basenode.children.append(node)
            node.set("creator", user.login_name)
            node.set("creationtime",  ustr(time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(time.time()))))
            db.session.commit()
            res = {'newid': node.id,
                   'id': req.params.get('id')}
            req.write(json.dumps(res, ensure_ascii=False))
            return None

        # create node using given identifier (doi, ...)
        if req.params.get('action') == "obj_from_identifier":
            identifier_importer = req.params.get('identifier_importer')
            identifier = req.params.get('identifier')

            logg.debug("... in %s.%s: going to create new node without file from identifier (%s)",
                __name__, funcname(), identifier)

            if identifier_importer in identifier_importers:
                identifierImporter = identifier_importers[identifier_importer]
                importer_func = identifierImporter.importer_func

                user = users.getUserFromRequest(req)
                importdir = users.getUploadDir(user)

                new_node = importer_func(identifier, importdir, req=req)

                res = {'id': req.params.get('id'), 'error': req.params.get('error', ''), 'error_detail': req.params.get('error_detail', '')}

                if new_node:
                    new_node.set("creator", user.login_name)
                    creation_time = ustr(time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(time.time())))
                    new_node.set("creationtime", creation_time)

                    new_node.set("system.identifier_importer", identifier_importer)
                    new_node.set("system.identifier_imported_from", identifier)

                    res['newid'] = new_node.id
                    db.session.commit()

                    logg.info("%s created new node id=%s (name=%s, type=%s) by importing identifier %s, "
                              "node is child of base node id=%s (name=%s, type=%s)", user.login_name, new_node.id, new_node.name, new_node.type,
                             identifier, importdir.id, importdir.name, importdir.type)
                else:  # import failed, no new_node created
                    logg.info("... in %s.%s: import failed, no new_node created for identifier (%s)", __name__, funcname(), identifier)

                req.write(json.dumps(res, ensure_ascii=False))

            # return value will be logged when level is DEBUG
            return None

        proceed_to_uploadcomplete = False
        # upload file to current node as attachment
        if req.params.get('action') == "upload":
            if 'file' in req.params:  # plupload
                realname = mybasename(req.params['file'].filename.decode("utf8"))
                tempname = req.params['file'].tempname.decode("utf8")
                proceed_to_uploadcomplete = True

            realname = realname.replace(' ', '_')
            # XXX: check this: import to realnamne or random name ?
            f = importFileToRealname(realname, tempname)
            node = q(Node).get(req.params.get('id'))
            node.files.append(f)
            db.session.commit()
            req.write("")
            logg.debug("%s|%s.%s: added file to node %s (%s, %s)", get_user_id(req), __name__, funcname(), node.id, node.name, node.type)
            if not proceed_to_uploadcomplete:
                return None

        # upload done -> deliver view of object
        if proceed_to_uploadcomplete or req.params.get('action') == "uploadcomplete":
            logg.debug("upload done -> deliver view of object")

            if proceed_to_uploadcomplete:
                req.params['file'] = realname

            mime = getMimeType(req.params.get('file'))
            data_extra = req.params.get('data_extra', '')
            if data_extra == 'tofile':

                ctx = {
                    'filename': f.getName(),
                }
                ctx.update(upload_to_filetype_filehandler(req))
                content = req.getTAL('web/edit/modules/upload.html', ctx, macro="uploadfileok_plupload")
                basenode = q(Node).get(req.params.get('id'))
                new_tree_labels = [{'id': basenode.id, 'label': getTreeLabel(basenode, lang=language)}]
                req.write(json.dumps({'type': 'file',
                                      'ret': content,
                                      'state': state,
                                      'filename': req.params.get('file'),
                                      'new_tree_labels': new_tree_labels}, ensure_ascii=False))
                return None

            if mime[1] == "other":  # file type not supported
                req.write(json.dumps({'type': mime[1],
                                      'ret': req.getTAL('web/edit/modules/upload.html', {}, macro="uploadfileerror"),
                                      'state': 'error',
                                      'filename': req.params.get('file')}, ensure_ascii=False))
                logg.debug("%s|%s.%s: added file to node %s (%s, %s) -> file type not supported",
                             get_user_id(req), __name__, funcname(), node.id, node.name, node.type)
                return None

            elif mime[1] == "zip":  # zip file
                if req.params.get('uploader', '') == 'plupload':
                    macro = "uploadzipfileok_plupload"
                else:
                    macro = "uploadzipfileok"
                content = req.getTAL('web/edit/modules/upload.html', upload_ziphandler(req), macro=macro)
            elif mime[1] == "bibtex":  # bibtex file
                if req.params.get('uploader', '') == 'plupload':
                    macro = "uploadbibfileok_plupload"
                else:
                    macro = "uploadbibfileok"
                content = req.getTAL('web/edit/modules/upload.html', upload_bibhandler(req), macro=macro)
            else:  # standard file
                if req.params.get('uploader', '') == 'plupload':
                    ctx = {
                        'filename': f.getName(),
                    }

                    ctx.update(upload_filehandler(req))

                    content = req.getTAL('web/edit/modules/upload.html', ctx, macro="uploadfileok_plupload")
                else:
                    content = req.getTAL('web/edit/modules/upload.html', upload_filehandler(req), macro="uploadfileok")
            basenode = q(Node).get(req.params.get('id'))
            new_tree_labels = [{'id': basenode.id, 'label': getTreeLabel(basenode, lang=language)}]
            _d = {
                  'type': mime[1],
                  'ret': content,
                  'state': state,
                  'filename': req.params.get('file'),
                  'new_tree_labels': new_tree_labels
            }

            req.write(json.dumps(_d, ensure_ascii=False))
            return None
    schemes = get_permitted_schemas()

    node = q(Node).get(ids[0])
    v = {}
    if node.isContainer():
        schemes = []
        dtypes = []

        if node.has_write_access():
            schemes = get_permitted_schemas()
            dtypes = getDatatypes(req, schemes)

        if "globalsort" in req.params:
            node.set("sortfield", req.params.get("globalsort"))
        v['collection_sortfield'] = node.get("sortfield")
        sortfields = [SortChoice(translation_t(req, "off"), "")]

        if node.type not in ["root", "collections", "home"]:
            sorted_schema_count = node.all_children_by_query(q(Node.schema, func.count(Node.schema)).group_by(Node.schema).order_by(func.count(Node.schema).desc()))

            for schema_count in sorted_schema_count:
                metadatatype = q(Metadatatype).filter_by(name=schema_count[0]).first()
                if metadatatype:
                    sort_fields = metadatatype.metafields.filter(Node.a.opts.like("%o%")).all()
                    if sort_fields:
                        for sortfield in sort_fields:
                            sortfields += [SortChoice(sortfield.getLabel(), sortfield.name)]
                            sortfields += [SortChoice(sortfield.getLabel() + translation_t(req, "descending"), "-" + sortfield.name)]
                        break

        v['sortchoices'] = sortfields
        v['count'] = len(node.content_children)
        v['language'] = lang(req)
        v['t'] = translation_t

    v.update({
        "id": req.params.get("id"),
        "sid": req.session.id,
        "datatypes": getDatatypes(req, schemes),
        "schemes": schemes,
        "uploadstate": req.params.get("upload"),
        "operations": showoperations(req, node),
        "nodelist": showdir(req, node),
    })
    return req.getTAL("web/edit/modules/upload.html", v, macro="upload_form")


# differs from os.path.split in that it handles windows as well as unix
# filenames
FNAMESPLIT = re.compile(r'(([^/\\]*[/\\])*)([^/\\]*)')


def mybasename(filename):
    g = FNAMESPLIT.match(filename)
    if g:
        basename =  g.group(3)
    else:
        basename = filename

    return basename

@dec_entry_log
def upload_filehandler(req):
    mime = getMimeType(req.params.get('file'))
    scheme_type = {mime[1]: []}
    for scheme in get_permitted_schemas():
        if mime[1] in scheme.getDatatypes():
            scheme_type[mime[1]].append(scheme)
            # break

    return {'files': [req.params.get('file')], 'schemes': scheme_type}


@dec_entry_log
def upload_to_filetype_filehandler(req):
    datatype = 'file'
    scheme_type = {datatype: []}
    for scheme in get_permitted_schemas():
        if datatype in scheme.getDatatypes():
            scheme_type[datatype].append(scheme)
            # break

    return {'files': [req.params.get('file')], 'schemes': scheme_type}


@dec_entry_log
def upload_ziphandler(req):
    schemes = get_permitted_schemas()
    files = []
    scheme_type = {}
    basenode = q(Node).get(req.params.get('id'))
    for file in basenode.files:
        if file.abspath.endswith(req.params.get('file')):
            z = zipfile.ZipFile(file.abspath)
            for f in z.namelist():
                #strip unwanted garbage from string
                name = mybasename(f).decode('utf8', 'ignore').encode('utf8')
                random_str = ustr(random.random())[2:]
                if name.startswith("._"):  # ignore Mac OS X junk
                    continue
                if name.split('.')[0] == '':
                    name = random_str + name

                files.append(name.replace(" ", "_"))
                _m = getMimeType(name)

                if random_str in name:
                    newfilename = join_paths(config.get("paths.tempdir"), name.replace(" ", "_"))
                else:
                    newfilename = join_paths(config.get("paths.tempdir"),  random_str + name.replace(" ", "_"))

                with codecs.open(newfilename, "wb") as fi:
                    fi.write(z.read(f))

                fn = importFileToRealname(mybasename(name.replace(" ", "_")), newfilename)
                basenode.files.append(fn)
                if os.path.exists(newfilename):
                    os.unlink(newfilename)

                if _m[1] not in scheme_type:
                    scheme_type[_m[1]] = []
                    for scheme in schemes:
                        if _m[1] in scheme.getDatatypes():
                            scheme_type[_m[1]].append(scheme)
            try:
                z.close()
                os.remove(file.abspath)
            except:
                pass
            basenode.files.remove(file)
            db.session.commit()
    return {'files': files, 'schemes': scheme_type}


@dec_entry_log
def upload_bibhandler(req):
    error = ""
    n = q(Node).get(req.params.get('id'))
    for f in n.files:
        if f.abspath.endswith(req.params.get('file')):
            try:
                retrieved_file = f.abspath
                logg.debug('going to call importBibTex(%s), import will be logged to backend!', retrieved_file)
                importBibTeX(retrieved_file)
                logg.info('importBibTex(%s) done, import logged to backend!', retrieved_file)
            except ValueError, e:
                logg.exception('calling importBibTex(%s)', retrieved_file)
                error = ustr(e)
            except MissingMapping, e:
                logg.exception('calling importBibTex(%s): missing mapping', retrieved_file)
                error = ustr(e)
            break
    return {'files': [req.params.get('file')], 'error': error}


# used in plugins?
def adduseropts(user):
    ret = []

    field = Node("upload.type_image", "metafield")
    field.set("label", "image_schema")
    field.set("type", "text")
    ret.append(field)
    field = Node("upload.type_text", "metafield")
    field.set("label", "text_schema")
    field.set("type", "text")
    ret.append(field)
    db.session.commit()
    return ret


def import_from_doi(identifier, importdir, req=None):

    def handle_error(req, error_msgstr):
        if req:
            errormsg = translation_t(req, error_msgstr)
            req.request["Location"] = req.makeLink("content", {"id": importdir.id, "error": errormsg})
            req.params["error"] = errormsg

    import schema.citeproc as citeproc
    import schema.importbase as importbase
    from requests.exceptions import ConnectionError
    doi = identifier
    logg.info("processing DOI import for: %s", doi)
    try:
        doi_extracted = citeproc.extract_and_check_doi(doi)
        new_node = citeproc.import_doi(doi_extracted, importdir)
        return new_node

    except citeproc.InvalidDOI:
        logg.error("Invalid DOI: '%s'", doi)
        handle_error(req, "doi_invalid")

    except citeproc.DOINotFound:
        logg.error("DOI not found: '%s'", doi)
        handle_error(req, "doi_unknown")

    except citeproc.DOINotImported:
        logg.error("no metadata imported for DOI: '%s'", doi)
        handle_error(req, "doi_no_metadata_imported")

    except importbase.NoMappingFound as e:
        logg.error("no mapping found for DOI: '%s', type '%s'", doi, e.typ)
        handle_error(req, "doi_type_not_mapped")

    except ConnectionError as e:
        logg.error("Connection to external server failed with error '%s'", e)
        handle_error(req, "doi_error_connecting_external_server")
    else:
        if req:
            req.request["Location"] = req.makeLink("content", {"id": importdir.id})


class IdentifierImporter(object):

    def __init__(self, name, importer_func):
        self.name = name
        self.importer_func = importer_func
        self.attrs = {}

    def set(self, attrname, attrval):
        self.attrs[attrname] = attrval

    def get(self, attrname, defaultval=None):
        return self.attrs.get(attrname, defaultval)


def register_identifier_importer(uniquename, identifierImporter):
    if uniquename in identifier_importers:
        raise KeyError("unique name %s for identifierImporter already used" % uniquename)
    else:
        identifier_importers[uniquename] = identifierImporter

doi_labels = {
    "de":
    [
        ("identifier_importer_longname", "Via DOI importieren"),
        ("identifier_importer_explain", u"""Um Metadaten für eine Publikation mit einem Digital Object Identifier zu importieren, bitte DOI eingeben und 'Objekt erzeugen' anklicken.
      <p>Beispiele:</p>
      doi:10.1371/journal.pbio.0020449
      <br/>DOI:10.1002/nme.4628 """),

        # error messages written by importer-function into request
        ("edit_import_nothing", 'Es wurde kein DOI angegeben.'),
        ("doi_unknown", 'Der angegebene DOI existiert nicht'),
        ("doi_invalid",
         u'Dies sieht nicht wie eine gültige DOI aus! (muss eine Zeichenkette enthalten, die mit 10. beginnt)'),
        ("doi_type_not_mapped",
         u'Für den Typ der angegebenen DOI ist kein Mapping definiert.'),
        ("doi_error_connecting_external_server",
         'Verbindungsfehler zum externen Server'),
    ],
    "en":
    [
        ("identifier_importer_longname", "Import via DOI"),
        ("identifier_importer_explain", """To import metadata for a publication with a Digital Object Identifier, please enter the DOI below and click 'Create Object'.
      <p>Examples:</p>
      doi:10.1371/journal.pbio.0020449
      <br/>DOI:10.1002/nme.4628 """),

        # error messages written by importer-function into request
        ("edit_import_nothing", 'No DOI was given.'),
        ("doi_unknown", "The specified DOI doesn't exist."),
        ("doi_invalid",
         "This doesn't look like an valid DOI (must contain a string starting with 10.)"),
        ("doi_type_not_mapped",
         'No mapping defined for type of given DOI.'),
        ("doi_error_connecting_external_server",
         'Error connecting to external server'),
    ]
}


doi_importer = IdentifierImporter('doi_importer', import_from_doi)
addLabels(doi_labels)  # make labels known to TAL interpreter
doi_importer.set('labels', {k: dict(v) for (k, v) in doi_labels.items()})
register_identifier_importer(doi_importer.name, doi_importer)
