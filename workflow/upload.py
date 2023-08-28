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

import mediatumtal.tal as _tal

import core.csrfform as _core_csrfform
import core.translation as _core_translation
from .workflow import WorkflowStep, registerStep
import utils.fileutils as fileutils
from utils.utils import OperationException
from .showdata import mkfilelist, mkfilelistshort
from core import db

logg = logging.getLogger(__name__)


def register():
    registerStep("workflowstep_upload")


class WorkflowStep_Upload(WorkflowStep):

    def show_workflow_node(self, node, req):
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
                orig_filename = file.filename
                file = fileutils.importFile(file.filename, file)
                node.files.append(file)
                node.name = orig_filename
                node.event_files_changed()
        db.session.commit()
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
                ),
                file="workflow/upload.html",
                macro="workflow_upload",
                request=req,
            )
