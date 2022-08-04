# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later


"""
This module defines the workflow step: upload.
Generates markup for the user page to upload a single file.
Generates markup for the admin page.
Accepted file types are configurable.
The module writes the new file to the database on success.
"""

from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from itertools import imap as map
from itertools import ifilter as filter
range = xrange

import logging
import hashlib as _hashlib

import mediatumtal.tal as _tal

import core as _core
import core.csrfform as _core_csrfform
import core.translation as _core_translation
from .workflow import WorkflowStep, registerStep
import utils.fileutils as fileutils
import utils.utils as _utils_utils
from .showdata import mkfilelist, mkfilelistshort

logg = logging.getLogger(__name__)
_known_prefix = "known_mimetypes_"

def register():
    registerStep("workflowstep_upload")

def _get_mimetype(f_extension):
    """
    Helper to get the mime type from a (partial) filename
    """
    mime_t = _utils_utils.getMimeType("_.{}".format(f_extension))

    if (mime_t != ("other", "other")):
        return mime_t[0]

class WorkflowStep_Upload(WorkflowStep):

    default_settings = dict(
        mimetypes = [],
    )

    def show_workflow_node(self, node, req):
        """
        Ask for exactly one document to upload. Overwrite any previously uploaded file.
        :param: mediatum node
        :param: client request
        :return: TAL template
        """
        error = ""

        for key in req.params.keys():
            if key.startswith("delete_"):
                filename = key[7:-2]
                all = 0
                for file in node.files:
                    if file.base_name == filename:
                        if file.type in ['document', 'image']:  # original -> delete all
                            all = 1
                        node.files.remove(file)

                if all == 1:  # delete all files
                    for file in node.files:
                        node.files.remove(file)

        if "file" in req.files:
            file = req.files["file"]
            if not file:
                error = _core_translation.translate_in_request("workflowstep_file_not_uploaded", req)
            else:
                if _get_mimetype(file.filename) in self.settings["mimetypes"]:
                    for f in node.files:
                        node.files.remove(f)

                    orig_filename = file.filename
                    file = fileutils.importFile(file.filename, file)
                    node.files.append(file)
                    node.name = orig_filename
                    node.event_files_changed()
        _core.db.session.commit()
        if "gotrue" in req.params:
            if hasattr(node, "event_files_changed"):
                node.event_files_changed()
            if len(node.files) > 0:
                return self.forwardAndShow(node, True, req)
            elif not error:
                error = _core_translation.translate_in_request("no_file_transferred", req)

        if "gofalse" in req.params:
            if hasattr(node, "event_files_changed"):
                node.event_files_changed()
            # if len(node.getFiles())>0:
            return self.forwardAndShow(node, False, req)
            # else:
            #    error = t(req, "no_file_transferred")

        filelist = mkfilelist(node, 1, request=req)
        filelistshort = mkfilelistshort(node, 1, request=req)

        return _tal.processTAL(
                dict(
                    obj=node.id,
                    id=self.id,
                    filelist=filelist,
                    filelistshort=filelistshort,
                    node=node,
                    buttons=self.tableRowButtons(node),
                    error=error,
                    pretext=self.getPreText(_core_translation.set_language(req.accept_languages)),
                    posttext=self.getPostText(_core_translation.set_language(req.accept_languages)),
                    csrf=_core_csrfform.get_token(),
                    mimetypes=",".join(self.settings["mimetypes"])
                ),
                file="workflow/upload.html",
                macro="workflow_upload",
                request=req,
            )
    def admin_settings_get_html_form(self, req):
        """
        Implementation of abstract base class method.
        Extends the default workflow step settings page with additional form fields to restrict file uploads.
        Add new file extensions. Translate to mime types. Delete set mime types.

        :param req: The request object
        :return: Additional html form fields for this workflow step
        """
        return _tal.processTAL(
            dict(
                mimetype_repr = {_hashlib.sha256(m).hexdigest(): m for m in self.settings["mimetypes"]},
                known_prefix = _known_prefix,
            ),
            file="workflow/upload.html",
            macro="workflow_step_type_config",
            request=req,
        )

    def admin_settings_save_form_data(self, data):
        """
        Implementation of abstract base class method.
        Extract accepted mimetypes from form data to self.settings
        and write it to database.

        :param data: ImmutabeleMultiDict is extracted from elements
                     with 'stepsetting_' prefixed name attribute
        """
        data = data.to_dict()
        new_mimetypes = frozenset(filter(None, map(_get_mimetype, data.pop("new_extensions").splitlines())))
        deletable_mimetypes = frozenset(data.pop("deletable_mimetypes").splitlines())

        # The remainder in data are the kept MIME types
        for d in data:
            assert(d.startswith(_known_prefix))

        kept_mimetypes = frozenset(map(lambda h: h[len(_known_prefix):], data))

        settings = self.settings
        hashes = {_hashlib.sha256(m).hexdigest(): m for m in settings["mimetypes"]}

        # Remove a MIME type only if it is in deletable_mimetypes
        for k in deletable_mimetypes - kept_mimetypes:
            del hashes[k]

        settings["mimetypes"] = tuple(new_mimetypes.union(hashes.itervalues()))
        self.settings = settings

        _core.db.session.commit()
