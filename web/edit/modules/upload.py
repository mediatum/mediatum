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
import core.users as users
import core.tree as tree
import core.acl as acl
import re
import utils.date
from utils.log import logException
import core.config as config
import zipfile
import PIL.Image
import random
import time
import logging

import json

from core.datatypes import loadAllDatatypes
from web.edit.edit_common import showdir, showoperations
from web.edit.edit import getTreeLabel, clearFromCache
import utils.date as date
from utils.utils import join_paths, OperationException, EncryptionException, formatException, getMimeType, funcname, get_user_id, log_func_entry, dec_entry_log, u2
from utils.fileutils import importFile, importFileToRealname
from schema.bibtex import importBibTeX, MissingMapping

from core.tree import Node
from core.acl import AccessData
from schema.schema import loadTypesFromDB

from core.translation import translate, lang, addLabels
from core.translation import t as translation_t

from pprint import pprint as pp, pformat as pf

logger = logging.getLogger('editor')

identifier_importers = {}


class SortChoice:

    def __init__(self, label, value):
        self.label = label
        self.value = value


def getInformation():
    return {"version": "1.1", "system": 0}


def elemInList(list, name):
    for item in list:
        if item.getName() == name:
            return True
    return False


@dec_entry_log
def getSchemes(req):
    schemes = AccessData(req).filter(loadTypesFromDB())
    return filter(lambda x: x.isActive(), schemes)


@dec_entry_log
def getDatatypes(req, schemes):
    dtypes = []
    datatypes = loadAllDatatypes()
    for scheme in schemes:
        for dtype in scheme.getDatatypes():
            if dtype not in dtypes:
                for t in datatypes:
                    if t.getName() == dtype and not elemInList(dtypes, t.getName()):
                        dtypes.append(t)

    dtypes.sort(lambda x, y: cmp(translate(x.getLongName(), request=req).lower(
    ), translate(y.getLongName(), request=req).lower()))
    return dtypes


def getSchemesforType(access, datatype):
    schemes = access.filter(loadTypesFromDB())
    ret = []
    for scheme in filter(lambda x: x.isActive(), schemes):
        if datatype in scheme.getDatatypes():
            ret.append(scheme)
    return ret


@dec_entry_log
def getContent(req, ids):

    user = users.getUserFromRequest(req)
    access = AccessData(user=user)
    language = lang(req)

    if "action" in req.params:
        state = 'ok'

        if req.params.get('action') == "removefiles":
            basenode = tree.getNode(req.params.get('id'))
            for f in basenode.getFiles():
                try:
                    os.remove(f.retrieveFile())
                    pass
                except:
                    state = "error"
            for f in basenode.getFiles():
                basenode.removeFile(f)
            req.write(json.dumps({'state': state}))
            return None

        if req.params.get('action') == "buildnode":  # create nodes
            basenode = tree.getNode(req.params.get('id'))
            newnodes = []
            errornodes = []
            basenodefiles_processed = []
            if req.params.get('uploader', '') == 'plupload':
                filename2scheme = {}
                for k in req.params:
                    if k.startswith("scheme_"):
                        filename2scheme[
                            k.replace('scheme_', '', 1)] = req.params.get(k)

                for f in basenode.getFiles():
                    filename = f.getName()
                    if filename in filename2scheme:
                        _m = getMimeType(filename)

                        if _m[1] == "bibtex":  # bibtex import handler
                            try:
                                nn = importBibTeX(f.retrieveFile(), basenode)
                                newnodes.append(nn.id)
                                basenodefiles_processed.append(f)
                            except ValueError, e:
                                errornodes.append((filename, str(e)))

                        logger.debug(
                            "filename: %r, mimetype: %r" % (filename, _m))
                        logger.debug(
                            "__name__=%r, func=%r; _m=%r, _m[1]=%r" % (__name__, funcname(), _m, _m[1]))

                        node_type = '%s/%s' % (_m[1],
                                               filename2scheme[filename])

                        n = tree.Node(filename, type=node_type)

                        basenode.addChild(n)
                        n.set("creator", user.getName())
                        n.set("creationtime",  str(
                            time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(time.time()))))

                        n.addFile(f)

                        n.event_files_changed()
                        clearFromCache(n)
                        newnodes.append(n.id)
                        basenodefiles_processed.append(f)
                        basenode.removeFile(f)
                        msg_t = (user.getName(), n.id, n.name, n.type,
                                 filename, basenode.id, basenode.name, basenode.type)
                        msg = "%s created new node id=%r (name=%r, type=%r) by uploading file %r, node is child of base node id=%r (name=%r, type=%r)" % msg_t
                        logger.info(msg)
                        logging.getLogger('usertracing').info(msg)

            else:
                for filename in req.params.get('files').split('|'):
                    _m = getMimeType(filename)
                    logger.debug("... in %s.%s: getMimeType(filename=%r)=%r" % (
                        __name__, funcname(), filename, _m))
                    fs = basenode.getFiles()
                    logger.debug("... in %s.%s: basenode.id=%r, basenode_files: %r" % (
                        __name__, funcname(), basenode.id, [(x.getName(), x.retrieveFile()) for x in fs]))
                    if _m[1] == req.params.get('type') or req.params.get('type') == 'file':
                        for f in basenode.getFiles():
                            # ambiguity here ?
                            if f.retrieveFile().endswith(filename):
                                # bibtex import handler
                                if _m[1] == "bibtex" and not req.params.get('type') == 'file':
                                    try:
                                        nn = importBibTeX(f.retrieveFile(), basenode)
                                        newnodes.append(nn.id)
                                        basenodefiles_processed.append(f)
                                    except ValueError, e:
                                        errornodes.append((filename, str(e)))
                                else:

                                    logger.debug(
                                        "creating new node: filename: %r" % filename)
                                    logger.debug("files at basenode: %r" % [
                                                 (x.getName(), x.retrieveFile()) for x in basenode.getFiles()])

                                    n = tree.Node(
                                        filename, type='%s/%s' % (req.params.get('type'), req.params.get('value')))
                                    basenode.addChild(n)
                                    n.set("creator", user.getName())
                                    n.set("creationtime",  str(
                                        time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(time.time()))))
                                    # clones to a file with random name
                                    cloned_file = f.clone(None)
                                    n.addFile(cloned_file)
                                    if hasattr(n, 'event_files_changed'):
                                        n.event_files_changed()
                                    clearFromCache(n)
                                    newnodes.append(n.id)
                                    basenodefiles_processed.append(f)
                                    msg_t = (user.getName(
                                    ), n.id, n.name, n.type, filename, basenode.id, basenode.name, basenode.type)
                                    msg = "%s created new node id=%r (name=%r, type=%r) by uploading file %r, node is child of base node id=%r (name=%r, type=%r)" % msg_t
                                    logger.info(msg)
                                    logging.getLogger('usertracing').info(msg)
                                    break  # filename may not be unique

            new_tree_labels = [
                {'id': basenode.id, 'label': getTreeLabel(basenode, lang=language)}]
            for f in basenodefiles_processed:
                basenode.removeFile(f)
                f_path = f.retrieveFile()
                if os.path.exists(f_path):
                    logger.debug(
                        "%s going to remove file %r from disk" % (user.getName(), f_path))
                    os.remove(f_path)

            mime = getMimeType(filename)
            scheme_type = {mime[1]: []}
            for scheme in getSchemes(req):
                if mime[1] in scheme.getDatatypes():
                    scheme_type[mime[1]].append(scheme)
                    # break

            # standard file
            content = req.getTAL(
                'web/edit/modules/upload.html', {'files': [filename], 'schemes': scheme_type}, macro="uploadfileok")

            res = json.dumps({'state': state, 'newnodes': newnodes, 'errornodes':
                              errornodes, 'new_tree_labels': new_tree_labels, 'ret': content})
            req.write(res)
            return None

        # add new object, only metadata
        if req.params.get('action') == "addmeta":
            schemes = getSchemes(req)
            dtypes = getDatatypes(req, schemes)
            if len(dtypes) == 1:  # load schemes for type
                schemes = getSchemesforType(access, dtypes[0].getName())
            content = req.getTAL('web/edit/modules/upload.html', {"datatypes": dtypes,
                                                                  "schemes": schemes,
                                                                  "language": lang(req),
                                                                  "identifier_importers": identifier_importers.values()}, macro="addmeta")

            req.write(json.dumps({'content': content}))
            return None

        # deliver schemes for given contenttype
        if req.params.get('action') == 'getschemes':
            ret = []
            for scheme in getSchemesforType(access, req.params.get('contenttype')):
                ret.append(
                    {'id': scheme.getName(), 'name': scheme.getLongName()})
            req.write(json.dumps({'schemes': ret}))
            return None

        # create node with given type/schema
        if req.params.get('action') == "createobject":
            print "\n\ncreate new node without file"
            schema = req.params.get('schema')
            ctype = req.params.get('contenttype')

            n = tree.Node('', type=ctype + '/' + schema)
            basenode = tree.getNode(req.params.get('id'))
            basenode.addChild(n)
            n.set("creator", user.getName())
            n.set("creationtime",  str(
                time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(time.time()))))
            clearFromCache(n)
            req.write(json.dumps({'newid': n.id, 'id': req.params.get('id')}))
            return None

        # create node using given identifier (doi, ...)
        if req.params.get('action') == "obj_from_identifier":
            identifier_importer = req.params.get('identifier_importer')
            identifier = req.params.get('identifier')

            msg = "... in %s.%s: going to create new node without file from identifier (%r)" % (
                __name__, funcname(), identifier)
            logger.debug(msg)

            if identifier_importer in identifier_importers:
                identifierImporter = identifier_importers[identifier_importer]
                importer_func = identifierImporter.importer_func

                user = users.getUserFromRequest(req)
                importdir = users.getUploadDir(user)

                new_node = importer_func(identifier, importdir, req=req)

                res = {'id': req.params.get('id'), 'error': req.params.get(
                    'error', ''), 'connect_error_msg': req.params.get('connect_error_msg', '')}

                if new_node:
                    new_node.set("creator", user.getName())
                    creation_time = str(
                        time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(time.time())))
                    new_node.set("creationtime", creation_time)

                    new_node.set(
                        "system.identifier_importer", identifier_importer)
                    new_node.set("system.identifier_imported_from", identifier)

                    clearFromCache(new_node)
                    res['newid'] = new_node.id

                    msg_t = (user.getName(), new_node.id, new_node.name, new_node.type,
                             identifier, importdir.id, importdir.name, importdir.type)
                    msg = "%s created new node id=%r (name=%r, type=%r) by importing identifier %r, node is child of base node id=%r (name=%r, type=%r)" % msg_t
                    logger.info(msg)
                    logging.getLogger("usertracing").info(msg)
                else:  # import failed, no new_node created
                    logger.error("... in %s.%s: import failed, no new_node created for identifier (%r)" % (
                        __name__, funcname(), identifier))

                req.write(json.dumps(res))

            # return value will be logged when level is DEBUG
            return None

        proceed_to_uploadcomplete = False
        # upload file to current node as attachment
        if req.params.get('action') == "upload":
            if 'file' in req.params:  # plupload
                realname = mybasename(req.params['file'].filename)
                tempname = req.params['file'].tempname
                msg = []
                for k in dir(req.params['file']):
                    if k in ['__doc__', '__init__', '__module__', '__str__', 'adddata', 'close', ]:
                        continue
                    msg.append("%r: %r" % (k, getattr(req.params['file'], k)))
                msg = "... req.params['file'] = %r" % (', '.join(msg))
                logger.debug(msg)
                proceed_to_uploadcomplete = True

            realname = realname.replace(' ', '_')
            # check this: import to realnamne or random name ?
            f = importFileToRealname(realname, tempname)
            #f = importFile(realname,tempname)
            n = tree.getNode(req.params.get('id'))
            n.addFile(f)
            req.write("")
            logger.debug("%r|%s.%s: added file to node %r (%r, %r)" % (
                get_user_id(req), __name__, funcname(), n.id, n.name, n.type))
            if not proceed_to_uploadcomplete:
                return None

        # upload done -> deliver view of object
        if proceed_to_uploadcomplete or req.params.get('action') == "uploadcomplete":
            logger.debug("upload done -> deliver view of object")

            if proceed_to_uploadcomplete:
                req.params['file'] = realname

            mime = getMimeType(req.params.get('file'))
            data_extra = req.params.get('data_extra', '')
            if data_extra == 'tofile':

                ctx = {
                    'filename': f.getName(),
                }
                ctx.update(upload_to_filetype_filehandler(req))
                content = req.getTAL(
                    'web/edit/modules/upload.html', ctx, macro="uploadfileok_plupload")
                basenode = tree.getNode(req.params.get('id'))
                new_tree_labels = [
                    {'id': basenode.id, 'label': getTreeLabel(basenode, lang=language)}]
                req.write(json.dumps({'type': 'file', 'ret': content, 'state': state, 'filename': req.params.get(
                    'file'), 'new_tree_labels': new_tree_labels}))
                return None

            if mime[1] == "other":  # file type not supported
                req.write(json.dumps({'type': mime[1], 'ret': req.getTAL(
                    'web/edit/modules/upload.html', {}, macro="uploadfileerror"), 'state': 'error', 'filename': req.params.get('file')}))
                logger.debug("%r|%s.%s: added file to node %r (%r, %r) -> file type not supported" %
                             (get_user_id(req), __name__, funcname(), n.id, n.name, n.type))
                return None

            elif mime[1] == "zip":  # zip file
                if req.params.get('uploader', '') == 'plupload':
                    macro = "uploadzipfileok_plupload"
                else:
                    macro = "uploadzipfileok"
                content = req.getTAL(
                    'web/edit/modules/upload.html', upload_ziphandler(req), macro=macro)
            elif mime[1] == "bibtex":  # bibtex file
                if req.params.get('uploader', '') == 'plupload':
                    macro = "uploadbibfileok_plupload"
                else:
                    macro = "uploadbibfileok"
                content = req.getTAL(
                    'web/edit/modules/upload.html', upload_bibhandler(req), macro=macro)
            else:  # standard file
                if req.params.get('uploader', '') == 'plupload':
                    ctx = {
                        'filename': f.getName(),
                    }

                    ctx.update(upload_filehandler(req))

                    content = req.getTAL(
                        'web/edit/modules/upload.html', ctx, macro="uploadfileok_plupload")
                else:
                    content = req.getTAL(
                        'web/edit/modules/upload.html', upload_filehandler(req), macro="uploadfileok")
            basenode = tree.getNode(req.params.get('id'))
            new_tree_labels = [{'id': basenode.id, 'label': getTreeLabel(basenode, lang=language)}]
            _d = {
                  'type': mime[1],
                  'ret': content,
                  'state': state,
                  'filename': req.params.get('file'),
                  'new_tree_labels': new_tree_labels,
                 }
            req.write(json.dumps(_d))
            return None
    schemes = getSchemes(req)

    node = tree.getNode(ids[0])
    v = {}
    if node.isContainer():
        schemes = []
        dtypes = []

        access = acl.AccessData(req)
        if access.hasWriteAccess(node):
            schemes = getSchemes(req)
            dtypes = getDatatypes(req, schemes)

        col = node
        if "globalsort" in req.params:
            col.set("sortfield", req.params.get("globalsort"))
        v['collection_sortfield'] = col.get("sortfield")
        sortfields = [SortChoice(translation_t(req, "off"), "")]

        if col.type not in ["root", "collections", "home"]:
            for ntype, num in col.getAllOccurences(acl.AccessData(req)).items():
                if ntype.getSortFields():
                    for sortfield in ntype.getSortFields():
                        sortfields += [
                            SortChoice(sortfield.getLabel(), sortfield.getName())]
                        sortfields += [SortChoice(sortfield.getLabel() + translation_t(
                            req, "descending"), "-" + sortfield.getName())]
                    break
        v['sortchoices'] = sortfields
        v['count'] = len(node.getContentChildren())
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

    if isinstance(basename, unicode):
        return basename.encode('utf8')
    else:
        return basename

@dec_entry_log
def upload_filehandler(req):
    mime = getMimeType(req.params.get('file'))
    scheme_type = {mime[1]: []}
    for scheme in getSchemes(req):
        if mime[1] in scheme.getDatatypes():
            scheme_type[mime[1]].append(scheme)
            # break

    return {'files': [req.params.get('file')], 'schemes': scheme_type}


@dec_entry_log
def upload_to_filetype_filehandler(req):
    datatype = 'file'
    scheme_type = {datatype: []}
    for scheme in getSchemes(req):
        if datatype in scheme.getDatatypes():
            scheme_type[datatype].append(scheme)
            # break

    return {'files': [req.params.get('file')], 'schemes': scheme_type}


@dec_entry_log
def upload_ziphandler(req):
    schemes = getSchemes(req)
    files = []
    scheme_type = {}
    basenode = tree.getNode(req.params.get('id'))
    for file in basenode.getFiles():
        if file.retrieveFile().endswith(req.params.get('file')):
            z = zipfile.ZipFile(file.retrieveFile())
            for f in z.namelist():
                #strip unwanted garbage from string
                name = mybasename(f).decode('utf8', 'ignore').encode('utf8')
                random_str = str(random.random())[2:]
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

                fi = open(newfilename, "wb")
                fi.write(z.read(f))
                fi.close()

                fn = importFileToRealname(mybasename(name.replace(" ", "_")), newfilename)
                basenode.addFile(fn)
                if os.path.exists(newfilename):
                    os.unlink(newfilename)

                if _m[1] not in scheme_type:
                    scheme_type[_m[1]] = []
                    for scheme in schemes:
                        if _m[1] in scheme.getDatatypes():
                            scheme_type[_m[1]].append(scheme)
            try:
                z.close()
                os.remove(file.retrieveFile())
            except:
                pass
            basenode.removeFile(file)
    return {'files': files, 'schemes': scheme_type}


@dec_entry_log
def upload_bibhandler(req):
    error = ""
    n = tree.getNode(req.params.get('id'))
    for f in n.getFiles():
        if f.retrieveFile().endswith(req.params.get('file')):
            try:
                retrieved_file = f.retrieveFile()
                logger.debug(
                    'going to call importBibTex(%r), import will be logged to backend!' % retrieved_file)
                nn = importBibTeX(retrieved_file)
                logger.info(
                    'importBibTex(%r) done, import logged to backend!' % retrieved_file)
            except ValueError, e:
                logger.exception('calling importBibTex(%r)' % retrieved_file)
                error = str(e)
            except MissingMapping, e:
                logger.exception(
                    'calling importBibTex(%r): missing mapping' % retrieved_file)
                error = str(e)
            break
    return {'files': [req.params.get('file')], 'error': error}


# used in plugins?
def adduseropts(user):
    ret = []

    field = tree.Node("upload.type_image", "metafield")
    field.set("label", "image_schema")
    field.set("type", "text")
    ret.append(field)
    field = tree.Node("upload.type_text", "metafield")
    field.set("label", "text_schema")
    field.set("type", "text")
    ret.append(field)
    return ret


def import_from_doi(identifier, importdir, req=None):
    import schema.citeproc as citeproc
    import schema.importbase as importbase
    from requests.exceptions import ConnectionError
    doi = identifier
    logger.info("processing DOI import for: %s", doi)
    try:
        doi_extracted = citeproc.extract_and_check_doi(doi)
        new_node = citeproc.import_doi(doi_extracted, importdir)
        return new_node
    except citeproc.InvalidDOI:
        logger.error("Invalid DOI: '%s'", doi)
        if req:
            req.request["Location"] = req.makeLink(
                "content", {"id": importdir.id, "error": translation_t(req, "doi_invalid")})
            req.params["error"] = translation_t(req, "doi_invalid")
    except citeproc.DOINotFound:
        logger.error("DOI not found: '%s'", doi)
        if req:
            req.request["Location"] = req.makeLink(
                "content", {"id": importdir.id, "error": translation_t(req, "doi_unknown")})
            req.params["error"] = translation_t(req, "doi_unknown")
    except importbase.NoMappingFound as e:
        logger.error("no mapping found for DOI: '%s', type '%s'", doi, e.typ)
        if req:
            req.request["Location"] = req.makeLink(
                "content", {"id": importdir.id, "error": translation_t(req, "doi_type_not_mapped")})
            req.params["error"] = translation_t(req, "doi_type_not_mapped")
    except ConnectionError as e:
        msg = "Connection to external server failed: '%s', type '%s'" % (
            doi, e)
        logger.error(msg)
        if req:
            req.request["Location"] = req.makeLink("content", {
                                                   "id": importdir.id, "error": translation_t(req, "error_connecting_external_server")})
            req.params["error"] = translation_t(
                req, "doi_error_connecting_external_server")
            req.params["connect_error_msg"] = msg
    else:
        if req:
            req.request["Location"] = req.makeLink(
                "content", {"id": importdir.id})


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
        raise KeyError(
            "unique name %r for identifierImporter already used" % uniquename)
    else:
        identifier_importers[uniquename] = identifierImporter

doi_labels = {
    "de":
    [
        ("identifier_importer_longname", "Via DOI importieren"),
        ("identifier_importer_explain", """Um Metadaten f\xc3\xbcr eine Publikation mit einem Digital Object Identifier zu importieren, bitte DOI eingeben und 'Objekt erzeugen' anklicken.
      <p>Beispiele:</p> 
      doi:10.1371/journal.pbio.0020449
      <br/>DOI:10.1002/nme.4628 """),

        # error messages written by importer-function into request
        ("edit_import_nothing", 'Es wurde kein DOI angegeben.'),
        ("doi_unknown", 'Der angegebene DOI existiert nicht'),
        ("doi_invalid",
         'Dies sieht nicht wie eine g\xc3\xbcltige DOI aus! (muss eine Zeichenkette enthalten, die mit 10. beginnt)'),
        ("doi_type_not_mapped",
         'F\xc3\xbcr den Typ der angegebenen DOI ist kein Mapping definiert.'),
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
