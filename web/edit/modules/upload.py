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
import time
import logging

import json
import mediatumtal.tal as _tal
import utils.fileutils as _utils_fileutils
import utils.utils as _utils_utils

import web.edit.edit_common as _web_edit_edit_common
from web.edit.edit import getTreeLabel
from web.edit.edit_common import showoperations, searchbox_navlist_height
from utils.url import build_url_from_path_and_params
from schema.bibtex import importBibTeX, MissingMapping

from core.translation import translate, lang, addLabels
from core.translation import t as translation_t
from core import db
from contenttypes import Data
from core import Node
from schema.schema import Metadatatype, get_permitted_schemas, get_permitted_schemas_for_datatype
from sqlalchemy import func
from utils.compat import iteritems
from web.edit.edit_common import default_edit_nodes_per_page, edit_node_per_page_values, get_searchparams
from web.frontend.frame import render_edit_search_box
import urllib
import web.common.sort as _sort

logg = logging.getLogger(__name__)
identifier_importers = {}
q = db.query


def getInformation():
    return {"version": "1.1", "system": 0}


def elemInList(list, name):
    for item in list:
        if item.__name__.lower() == name:
            return True
    return False


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


def getContent(req, ids):

    user = users.user_from_session()
    language = lang(req)

    if "action" in req.values:
        state = 'ok'
        basenode = q(Node).get(req.values['id'])
        if req.values['action'] == "removefiles":
            for f in basenode.files:
                try:
                    os.remove(f.abspath)
                    pass
                except:
                    state = "error"
            basenode.files = []
            db.session.commit()
            req.response.set_data(json.dumps({'state': state}, ensure_ascii=False))
            return None

        if req.values['action'] == "buildnode":  # create nodes
            newnodes = []
            errornodes = []
            basenodefiles_processed = []

            for filename in req.values['files'].split('|'):
                mimetype = _utils_utils.getMimeType(filename)
                logg.debug("getMimeType(filename=%s)=%s", filename, mimetype)
                if req.values['type'] not in (mimetype[1], 'file'):
                    continue
                for f in basenode.files:
                    # ambiguity here ?
                    if not f.abspath.endswith(filename):
                        continue
                    # bibtex import handler
                    if mimetype[1] == "bibtex" and not req.values['type'] == 'file':
                        try:
                            new_node = importBibTeX(f.abspath, basenode, req=req)
                            newnodes.append(new_node.id)
                            basenodefiles_processed.append(f)
                        except ValueError, e:
                            errornodes.append((filename, translate(unicode(e), request=req), unicode(hash(f.getName()))))
                        db.session.commit()
                        continue

                    logg.debug("creating new node: filename: %s", filename)

                    content_class = Node.get_class_for_typestring(req.values['type'])
                    node = content_class(name=filename, schema=req.values['value'])

                    basenode.children.append(node)
                    node.set("creator", user.login_name)
                    node.set("creationtime",  unicode(time.strftime('%Y-%m-%dT%H:%M:%S',
                                                                    time.localtime(time.time()))))

                    # clones to a file with random name
                    cloned_file = _utils_fileutils.importFileRandom(f.abspath)
                    # set filetype for uploaded file as requested by the content class
                    cloned_file.filetype = content_class.get_upload_filetype()
                    node.files.append(cloned_file)
                    try:
                        node.event_files_changed()
                    except Exception as e:
                        errornodes.append((filename, translate(unicode(e), request=req), unicode(hash(f.getName()))))
                        db.session.rollback()
                        continue
                    newnodes.append(node.id)
                    basenodefiles_processed.append(f)

                    logg.info(
                            "%s created new node id=%s (name=%s, type=%s) by uploading file %s, "
                            "node is child of base node id=%s (name=%s, type=%s)",
                            user.login_name, node.id, node.name, node.type, filename, basenode.id, basenode.name, basenode.type
                        )

                    break  # filename may not be unique

            for f in basenodefiles_processed:
                basenode.files.remove(f)
                f_path = f.abspath
                if os.path.exists(f_path):
                    logg.debug("%s going to remove file %s from disk", user.login_name, f_path)
                    os.remove(f_path)

            mime = _utils_utils.getMimeType(filename)
            scheme_type = {mime[1]: []}
            for scheme in get_permitted_schemas():
                if mime[1] in scheme.getDatatypes():
                    scheme_type[mime[1]].append(scheme)
                    # break

            db.session.commit()
            # standard file
            req.response.set_data(json.dumps(
                dict(
                    state=state,
                    newnodes=newnodes,
                    errornodes=errornodes,
                    new_tree_labels=[dict(id=basenode.id, label=getTreeLabel(basenode, lang=language))],
                    ret=_tal.processTAL(
                            dict(files=[filename], schemes=scheme_type),
                            file='web/edit/modules/upload.html',
                            macro="uploadfileok",
                            request=req,
                        ),
                ),
                ensure_ascii=False,
            ))
            return None

        # add new object, only metadata
        if req.values['action'] == "addmeta":
            ret = []
            schemes = get_permitted_schemas()
            dtypes = getDatatypes(req, schemes)
            dtypenames = {t.__name__.lower():t.__name__ for t in dtypes}
            for scheme in get_permitted_schemas():
                datatypes = scheme.getDatatypes()
                for datatype in datatypes:
                    if datatype in dtypenames.keys():
                        ret.append(
                            dict(
                                id=scheme.name,
                                name=u'{} / {}'.format(scheme.getLongName(), translate(dtypenames[datatype], request=req)),
                                description=scheme.getDescription(), datatype=datatype,
                            ),
                        )
            if len(dtypes) == 1:  # load schemes for type
                schemes = get_permitted_schemas_for_datatype(dtypes[0].__name__.lower())

            req.response.set_data(json.dumps(
                dict(content=_tal.processTAL(
                    dict(
                        datatypes=dtypes,
                        schemes=ret,
                        language=lang(req),
                        identifier_importers=identifier_importers.values(),
                    ),
                    file='web/edit/modules/upload.html',
                    macro="addmeta",
                    request=req,
                )),
                ensure_ascii=False,
            ))
            return None

        # add new object, only doi
        if req.values['action'] == "adddoi":
            req.response.set_data(json.dumps(
                dict(content=_tal.processTAL(
                    dict(language=lang(req), identifier_importers=identifier_importers.values()),
                    file='web/edit/modules/upload.html',
                    macro="adddoi",
                    request=req,
                )),
                ensure_ascii=False,
            ))
            return None

        # deliver schemes for given contenttype
        if req.values['action'] == 'getschemes':
            ret = []
            for scheme in get_permitted_schemas_for_datatype(req.values.get('contenttype')):
                ret.append(dict(id=scheme.name, name=scheme.getLongName()))
            req.response.set_data(json.dumps(dict(schemes=ret), ensure_ascii=False))
            return None

        # create node with given type/schema
        if req.values['action'] == "createobject":
            schema = req.values.get('schema')
            ctype = req.values.get('contenttype')

            node = Node(name=u"", type=ctype, schema=schema)
            basenode.children.append(node)
            node.set("creator", user.login_name)
            node.set("creationtime",  ustr(time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(time.time()))))
            db.session.commit()
            req.response.set_data(json.dumps(dict(newid=node.id, id=req.values.get('id')), ensure_ascii=False))
            return None

        # create node using given identifier (doi, ...)
        if req.values['action'] == "obj_from_identifier":
            identifier_importer = req.values['identifier_importer']
            identifier = req.values['identifier']

            logg.debug("going to create new node without file from identifier (%s)", identifier)

            if identifier_importer in identifier_importers:
                identifierImporter = identifier_importers[identifier_importer]
                importer_func = identifierImporter.importer_func

                user = users.user_from_session()
                importdir = users.getUploadDir(user)

                new_node = importer_func(identifier, importdir, req=req)

                res = dict(id=req.values['id'], error=req.values.get('error', ''), error_detail=req.values.get('error_detail', ''))

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
                    logg.info("import failed, no new_node created for identifier (%s)", identifier)

                req.response.set_data(json.dumps(res, ensure_ascii=False))

            # return value will be logged when level is DEBUG
            return None

        proceed_to_uploadcomplete = False
        # upload file to current node as attachment
        if req.values['action'] == "upload":
            uploadfile = req.files["file"]
            proceed_to_uploadcomplete = True
            # XXX: check this: import to realnamne or random name ?
            incoming_file = _utils_fileutils.importFile(uploadfile.filename, uploadfile)
            node = q(Node).get(req.values['id'])
            node.files.append(incoming_file)
            db.session.commit()
            req.response.set_data("")
            logg.debug("%s: added file to node %s (%s, %s)", _utils_utils.get_user_id(), node.id, node.name, node.type)

        # upload done -> deliver view of object
        if proceed_to_uploadcomplete:
            logg.debug("upload done -> deliver view of object")
            mime = _utils_utils.getMimeType(uploadfile.filename)
            data_extra = req.values.get('data_extra', '')
            if data_extra == 'tofile':
                ctx = dict(filename=incoming_file.getName())
                ctx.update(upload_to_filetype_filehandler(uploadfile.filename))
                req.response.set_data(json.dumps(
                    dict(
                        type='file',
                        ret=_tal.processTAL(
                                  ctx,
                                  file='web/edit/modules/upload.html',
                                  macro="uploadfileok_plupload",
                                  request=req,
                              ),
                        state=state,
                        filename=uploadfile.filename,
                        new_tree_labels=[dict(id=basenode.id, label=getTreeLabel(basenode, lang=language))],
                    ),
                    ensure_ascii=False,
                ))
                return None

            if mime[1] == "other":  # file type not supported
                req.response.set_data(json.dumps(
                    dict(
                        type=mime[1],
                        ret=_tal.processTAL({}, file='web/edit/modules/upload.html', macro="uploadfileerror", request=req),
                        state='error',
                        filename=uploadfile.filename,
                    ),
                    ensure_ascii=False,
                ))
                logg.debug("%s|%s.%s: added file to node %s (%s, %s) -> file type not supported",
                             _utils_utils.get_user_id(), __name__, _utils_utils.funcname(), node.id, node.name, node.type)
                return None

            elif mime[1] == "zip":  # zip file
                if req.values.get('uploader', '') == 'plupload':
                    macro = "uploadzipfileok_plupload"
                else:
                    macro = "uploadzipfileok"
                content = _tal.processTAL(
                        upload_ziphandler(uploadfile.filename, req.values['id']),
                        file='web/edit/modules/upload.html',
                        macro=macro,
                        request=req,
                    )
            elif mime[1] == "bibtex":  # bibtex file
                if req.values.get('uploader', '') == 'plupload':
                    macro = "uploadbibfileok_plupload"
                else:
                    macro = "uploadbibfileok"
                content = _tal.processTAL(
                        upload_bibhandler(uploadfile.filename, req.values['id']),
                        file='web/edit/modules/upload.html',
                        macro=macro,
                        request=req,
                    )
            else:  # standard file
                if req.values.get('uploader', '') == 'plupload':
                    ctx = dict(filename=incoming_file.getName())
                    ctx.update(upload_filehandler(uploadfile.filename))
                    content = _tal.processTAL(
                            ctx,
                            file='web/edit/modules/upload.html',
                            macro="uploadfileok_plupload",
                            request=req,
                        )
                else:
                    content = _tal.processTAL(
                            upload_filehandler(uploadfile.filename),
                            file='web/edit/modules/upload.html',
                            macro="uploadfileok",
                            request=req,
                        )

            req.response.set_data(json.dumps(
                dict(
                    type=mime[1],
                    ret=content,
                    state=state,
                    filename=uploadfile.filename,
                    new_tree_labels=[dict(id=basenode.id, label=getTreeLabel(basenode, lang=language))],
                ),
                ensure_ascii=False,
            ))
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

        if "globalsort" in req.values:
            node.set("sortfield", req.values["globalsort"])
        if req.values.get("sortfield", "") != "":
            v['collection_sortfield'] = req.values.get("sortfield")
        else:
            v['collection_sortfield'] = node.get("sortfield")
        if req.values.get("nodes_per_page", "") != "":
            v['npp_field'] = req.values.get("nodes_per_page", default_edit_nodes_per_page)
        else:
            v['npp_field'] = node.get("nodes_per_page")
        if not v['npp_field']:
            v['npp_field'] = default_edit_nodes_per_page

        assert node.type not in ["root", "collections", "home"]

        v['language'] = lang(req)
        v['t'] = translation_t

    search_html = render_edit_search_box(q(Node).get(ids[0]), language, req, edit=True)
    searchmode = req.values.get("searchmode")
    item_count = []
    show_dir_nav = _web_edit_edit_common.ShowDirNav(req, node)
    items = show_dir_nav.showdir(sortfield=req.values.get("sortfield"), item_count=item_count)
    nav = show_dir_nav.shownav()
    navigation_height = searchbox_navlist_height(req, item_count)
    count = item_count[0] if item_count[0] == item_count[1] else "%d from %d" % (item_count[0], item_count[1])
    searchparams = get_searchparams(req)
    searchparams = {k: unicode(v).encode("utf8") for k, v in searchparams.items()}

    v.update(
        id=req.values["id"],
        datatypes=getDatatypes(req, schemes),
        schemes=schemes,
        uploadstate=req.values.get("upload"),
        operations=showoperations(req, node),
        nodelist=items,
        nav=nav,
        count=count,
        search=search_html,
        query=req.query_string.replace('id=', 'src='),
        searchparams=urllib.urlencode(searchparams),
        get_ids_from_query=",".join(show_dir_nav.get_ids_from_req()),
        edit_all_objects=translation_t(lang(req), "edit_all_objects").format(item_count[1]),
        navigation_height=navigation_height,
        csrf=str(req.csrf_token.current_token),
    )
    html = _tal.processTAL(v, file="web/edit/modules/upload.html", macro="upload_form", request=req)
    show_dir_nav.nodes = None
    return html


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


def upload_filehandler(filename):
    mime = _utils_utils.getMimeType(filename)
    scheme_type = {mime[1]: []}
    for scheme in get_permitted_schemas():
        if mime[1] in scheme.getDatatypes():
            scheme_type[mime[1]].append(scheme)
            # break

    return dict(files=[filename], schemes=scheme_type)


def upload_to_filetype_filehandler(filename):
    datatype = 'file'
    scheme_type = {datatype: []}
    for scheme in get_permitted_schemas():
        if datatype in scheme.getDatatypes():
            scheme_type[datatype].append(scheme)
            # break

    return dict(files=[filename], schemes=scheme_type)


def upload_ziphandler(filename, id):
    schemes = get_permitted_schemas()
    files = []
    scheme_type = {}
    basenode = q(Node).get(id)
    for file in basenode.files:
        if file.abspath.endswith(filename):
            z = zipfile.ZipFile(file.abspath)
            for f in z.namelist():
                #strip unwanted garbage from string
                name = mybasename(f).decode('utf8', 'ignore').encode('utf8')
                random_str = _utils_utils.gen_secure_token(128)
                if name.startswith("._"):  # ignore Mac OS X junk
                    continue
                if name.split('.')[0] == '':
                    name = random_str + name

                files.append(name.replace(" ", "_"))
                _m = _utils_utils.getMimeType(name)

                if random_str in name:
                    newfilename = _utils_utils.join_paths(config.get("paths.tempdir"), name.replace(" ", "_"))
                else:
                    newfilename = _utils_utils.join_paths(config.get("paths.tempdir"),  random_str + name.replace(" ", "_"))

                with codecs.open(newfilename, "wb") as fi:
                    fi.write(z.read(f))

                fn = _utils_fileutils.importFile(mybasename(name.replace(" ", "_")), z)
                basenode.files.append(fn)
                if os.path.exists(newfilename):
                    os.unlink(newfilename)

                if _m[1] not in scheme_type:
                    scheme_type[_m[1]] = []
                    for scheme in schemes:
                        if _m[1] in scheme.getDatatypes():
                            scheme_type[_m[1]].append(scheme)
            with _utils_utils.suppress(Exception, warn=False):
                z.close()
                os.remove(file.abspath)
            basenode.files.remove(file)
            db.session.commit()
    return dict(files=files, schemes=scheme_type)


def upload_bibhandler(filename, id):
    error = ""
    n = q(Node).get(id)
    for f in n.files:
        if f.abspath.endswith(filename):
            try:
                retrieved_file = f.abspath
                logg.debug('going to call importBibTex(%s), import will be logged to backend!', retrieved_file)
                importBibTeX(retrieved_file, req=True)
                logg.info('importBibTex(%s) done, import logged to backend!', retrieved_file)
            except ValueError, e:
                logg.exception('calling importBibTex(%s)', retrieved_file)
                error = ustr(e)
            except MissingMapping, e:
                logg.exception('calling importBibTex(%s): missing mapping', retrieved_file)
                error = ustr(e)
            break
    return dict(files=[filename], error=error)


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
            req.response.location = build_url_from_path_and_params("content", {"id": importdir.id, "error": errormsg})
            req.values["error"] = errormsg

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
            req.response.location = build_url_from_path_and_params("content", {"id": importdir.id})


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

doi_labels = dict(
    de=[
            ("identifier_importer_longname", "Via DOI importieren"),
            ("identifier_importer_explain", u"""Bitte DOI eingeben und <i>OK</i> klicken, um die Metadaten einer Publikation in mediaTUM zu importieren.
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
    en=[
            ("identifier_importer_longname", "Import via DOI"),
            ("identifier_importer_explain", """Please enter DOI to import metadata of publication.
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
        ],
)


doi_importer = IdentifierImporter('doi_importer', import_from_doi)
addLabels(doi_labels)  # make labels known to TAL interpreter
doi_importer.set('labels', {k: dict(v) for (k, v) in doi_labels.items()})
register_identifier_importer(doi_importer.name, doi_importer)
