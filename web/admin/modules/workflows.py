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
from __future__ import division
from __future__ import print_function

import logging
import re
import sys
import traceback
import mediatumtal.tal as _tal

import core.config as config

from workflow.workflow import Workflow, getWorkflowList, getWorkflow, updateWorkflow, addWorkflow, deleteWorkflow, \
    inheritWorkflowRights, getWorkflowTypes, create_update_workflow_step, deleteWorkflowStep, exportWorkflow, importWorkflow
from web.admin.adminutils import Overview, getAdminStdVars, getFilter, getSortCol
from schema.schema import parseEditorData
from web.common.acl_web import makeList
from utils.utils import removeEmptyStrings
from core.translation import t, lang
from core import db, Node as _Node
from core.database.postgres.permission import NodeToAccessRuleset

logg = logging.getLogger(__name__)


def getInformation():
    return{"version": "1.0"}

""" standard validator to execute correct method """


def _aggregate_workflowstep_text_parameters(req_values, languages):
    """
    Parse workflow step http parameters from req_values dict,
    return dict with values.
    If languages are defined, parameters in req_values are expected
    to be prefixed with "{language}.n", otherwise just "n".
    Return dict values contain texts of all languages,
    prefixed with "{language}:" and newline-separated,
    or just the language-independent content.
    """
    # generate a list of request parameter prefixes for each language,
    # e.g. ("de.n", "en.n"),
    # or just generate a single prefix "n" if no languages are defined
    lang_prefixes = {"{}.n".format(lang): "{}:".format(lang) for lang in languages} or {"n": ""}
    labeltexts = dict()
    for key in u"truelabel falselabel sidebartext pretext posttext".split():
        labeltexts[key] = u"\n".join(
            u"{}{}".format(v, req_values[u"{}{}".format(k, key)].replace("\n", ""))
            for k, v in lang_prefixes.iteritems()
        )
    for key in u"name trueid falseid comment".split():
        labeltexts[key] = req_values[u"n{}".format(key)]

    return labeltexts


def validate(req, op):
    path = req.mediatum_contextfree_path[1:].split("/")
    if len(path) == 3 and path[2] == "overview":
        return WorkflowPopup(req)

    # import scheme from xml-file
    importfile = req.files.get("file")
    if importfile:
        importWorkflow(importfile)

    if req.values.get("form_op", "") == "update":
        return WorkflowStepDetail(req, req.values["parent"], req.values["nname"], -1)

    try:

        if req.values.get("acttype", "workflow") == "workflow":
            # workflow section
            for key in req.values:
                if key.startswith("new_"):
                    # create new workflow
                    return WorkflowDetail(req, "")

                elif key.startswith("edit_"):
                    # edit workflow
                    return WorkflowDetail(req, unicode(key[5:-2]))

                elif key.startswith("delete_"):
                    # delete workflow
                    deleteWorkflow(key[7:-2])
                    break

                elif key.startswith("detaillist_"):
                    # show nodes for given workflow
                    return WorkflowStepList(req, key[11:-2])

            if "form_op" in req.values:
                if req.values["form_op"] == "cancel":
                    return view(req)

                if not req.values["name"]:
                    return WorkflowDetail(req, req.values["id"], 1)  # no name was given

                if req.values["form_op"] == "save_new":
                    # save workflow values
                    wf = addWorkflow(req.values["name"], req.values["description"])
                elif req.values["form_op"] == "save_edit":
                    # save workflow values
                    wf = updateWorkflow(
                            req.values["name"],
                            req.values["description"],
                            req.values["name_attr"],
                            req.values["orig_name"],
                        )
                else:
                    raise AssertionError("invalid form_op")

                language_list = filter(lambda lang : "wf_language_{}".format(lang) in req.values, config.languages)
                if language_list:
                    wf.set('languages', ';'.join(language_list))
                else:
                    wf.attrs.pop("languages", None)

                for r in wf.access_ruleset_assocs.filter_by(ruletype=u'read'):
                    db.session.delete(r)

                for key in req.values:
                    if key.startswith("left_read"):
                        for r in req.values.getlist(key):
                            wf.access_ruleset_assocs.append(NodeToAccessRuleset(ruleset_name=r, ruletype=key[9:]))
                        break

                for r in wf.access_ruleset_assocs.filter_by(ruletype=u'write'):
                    db.session.delete(r)

                for key in req.values:
                    if key.startswith("left_write"):
                        for r in req.values.getlist(key):
                            wf.access_ruleset_assocs.append(NodeToAccessRuleset(ruleset_name=r, ruletype=key[10:]))
                        break

                # check for right inheritance
                if "write_inherit" in req.values:
                    inheritWorkflowRights(req.values["name"], "write")
                if "read_inherit" in req.values:
                    inheritWorkflowRights(req.values["name"], "read")
                db.session.commit()

        else:
            # workflowstep section
            for key in req.values:
                if key.startswith("newdetail_"):
                    # create new workflow
                    return WorkflowStepDetail(req, req.values["parent"], "")
                elif key.startswith("editdetail_"):
                    # edit workflowstep
                    return WorkflowStepDetail(req, req.values["parent"], key[11:-2].split("|")[1])
                elif key.startswith("deletedetail_"):
                    # delete workflow step id: deletedetail_[workflowid]|[stepid]
                    deleteWorkflowStep(key[13:-2].split("|")[0], key[13:-2].split("|")[1])
                    break

            if "form_op" in req.values:
                if req.values["form_op"] == "cancel":
                    return WorkflowStepList(req, req.values["parent"])

                if not req.values["nname"]:  # no Name was given
                    return WorkflowStepDetail(req, req.values["parent"], req.values["stepid"], 1)

                workflow = getWorkflow(req.values["parent"])
                if req.values["form_op"] == "save_newdetail":
                    # save workflowstep values -> create
                    # don't create a new workflowstep if a workflowstep with the same name already exists
                    workflowstep = workflow.getStep(req.values["nname"], test_only=True)
                    if workflowstep:
                        raise ValueError("a workflowstep with the same name already exists")

                    wnode = create_update_workflow_step(
                            typ=req.values["ntype"],
                            adminstep=req.values.get("adminstep", ""),
                            **_aggregate_workflowstep_text_parameters(
                                req.values,
                                workflow.getLanguages(),
                            )
                        )
                    workflow.addStep(wnode)

                elif req.values["form_op"] == "save_editdetail":
                    # update workflowstep
                    # don't update a workflowstep if the name is changed and a workflowstep with the same name already exists
                    if req.values["orig_name"] != req.values["nname"]:
                        workflowstep = workflow.getStep(req.values["nname"], test_only=True)
                        if workflowstep:
                            raise ValueError("a workflowstep with the same name already exists")

                    wnode = create_update_workflow_step(
                            workflow.getStep(req.values["orig_name"]),
                            adminstep=req.values.get("adminstep", ""),
                            typ=req.values["ntype"],
                            **_aggregate_workflowstep_text_parameters(
                                req.values,
                                workflow.getLanguages(),
                            )
                        )
                else:
                    raise AssertionError("invalid form_op")

                wnode = workflow.getStep(wnode.name)
                for r in wnode.access_ruleset_assocs.filter_by(ruletype=u'read'):
                    db.session.delete(r)

                for key in req.values:
                    if key.startswith("left_read"):
                        for r in req.values.getlist(key):
                            wnode.access_ruleset_assocs.append(NodeToAccessRuleset(ruleset_name=r, ruletype=key[9:]))
                        break

                for r in wnode.access_ruleset_assocs.filter_by(ruletype=u'write'):
                    db.session.delete(r)

                for key in req.values:
                    if key.startswith("left_write"):
                        for r in req.values.getlist(key):
                            wnode.access_ruleset_assocs.append(NodeToAccessRuleset(ruleset_name=r, ruletype=key[10:]))
                        break
                db.session.commit()

                if "metaDataEditor" in req.values:
                    parseEditorData(req, wnode)

            return WorkflowStepList(req, req.values["parent"])

        return view(req)
    except Exception as ex:
        logg.exception("exception in validate")
        return '<h3 style="color: red">%s</h3>' % ex.message


""" overview of all defined workflows
    parameter: req=request """


def view(req):
    workflows = list(getWorkflowList())
    order = getSortCol(req)
    actfilter = getFilter(req)
    # filter
    if actfilter != "":
        if actfilter in ("all", "*", t(lang(req), "admin_filter_all")):
            None  # all users
        elif actfilter == "0-9":
            num = re.compile(r'([0-9])')
            workflows = filter(lambda x: num.match(x.name), workflows)
        elif actfilter == "else" or actfilter == t(lang(req), "admin_filter_else"):
            all = re.compile(r'([a-z]|[A-Z]|[0-9])')
            workflows = filter(lambda x: not all.match(x.name), workflows)
        else:
            workflows = filter(lambda x: x.name.lower().startswith(actfilter), workflows)

    pages = Overview(req, workflows)

    # sorting
    if order != "":
        if int(order[0:1]) == 1:
            workflows.sort(lambda x, y: cmp(x.name, y.name))
        elif int(order[0:1]) == 2:
            workflows.sort(lambda x, y: cmp(x.getDescription(), y.getDescription()))
        # elif int(order[0:1]) == 3:
            # workflows.sort(lambda x, y: cmp(x.getAccess("read"), y.getAccess("read")))
        # elif int(order[0:1]) == 4:
            # workflows.sort(lambda x, y: cmp(x.getAccess("write"), y.getAccess("write")))
        if int(order[1:]) == 1:
            workflows.reverse()

    v = getAdminStdVars(req)
    v["sortcol"] = pages.OrderColHeader([t(lang(req), "admin_wf_col_{}".format(col)) for col in xrange(1, 5)])
    v["workflows"] = workflows
    v["pages"] = pages
    v["actfilter"] = actfilter
    v["csrf"] = req.csrf_token.current_token
    return _tal.processTAL(v, file="web/admin/modules/workflows.html", macro="view", request=req)

""" edit form for given workflow (create/update)
    parameter: req=request, id=workflowid (name), err=error code as integer """


def WorkflowDetail(req, id, err=0):
    v = getAdminStdVars(req)
    if err == 0 and id == "":
        # new workflow
        workflow = Workflow(u"")
        db.session.commit()
        v["original_name"] = ""

    elif id != "" and err == 0:
        # edit workflow
        workflow = getWorkflow(id)
        v["original_name"] = workflow.name

    else:
        # error
        workflow = Workflow(u"")
        workflow.name = req.values["name"]
        workflow.set("description", req.values["description"])
        v["original_name"] = req.values["orig_name"]
        workflow.id = req.values["id"]
        db.session.commit()

    try:
        rule = {
                "read": [r.ruleset_name for r in workflow.access_ruleset_assocs.filter_by(ruletype='read')],
                "write": [r.ruleset_name for r in workflow.access_ruleset_assocs.filter_by(ruletype='write')],
            }
    except:
        rule = {"read": [], "write": []}

    v["acl_read"] = makeList(req, "read", removeEmptyStrings(rule["read"]), {}, overload=0, type="read")
    v["acl_write"] = makeList(req, "write", removeEmptyStrings(rule["write"]), {}, overload=0, type="write")
    v["workflow"] = workflow
    v["languages"] = config.languages
    v["error"] = err
    v["actpage"] = req.values["actpage"]
    v["csrf"] = req.csrf_token.current_token
    return _tal.processTAL(v, file="web/admin/modules/workflows.html", macro="modify", request=req)

""" overview of all steps for given workflow
    parameter: req=request, wid=wordflow id (name) """


def WorkflowStepList(req, wid):
    global _cssclass, _page
    workflow = getWorkflow(wid)
    workflowsteps = list(workflow.getSteps())
    order = getSortCol(req)
    actfilter = getFilter(req)

    # filter
    if actfilter != "":
        if actfilter in ("all", "*", t(lang(req), "admin_filter_all")):
            None  # all users
        elif actfilter == "0-9":
            num = re.compile(r'([0-9])')
            workflowsteps = filter(lambda x: num.match(x.name), workflowsteps)
        elif actfilter == "else" or actfilter == t(lang(req), "admin_filter_else"):
            all = re.compile(r'([a-z]|[A-Z]|[0-9])')
            workflowsteps = filter(lambda x: not all.match(x.name), workflowsteps)
        else:
            workflowsteps = filter(lambda x: x.name.lower().startswith(actfilter), workflowsteps)

    pages = Overview(req, workflowsteps)

    # sorting
    if order != "":
        if int(order[0]) == 0:
            workflowsteps.sort(lambda x, y: cmp(x.name.lower(), y.name.lower()))
        elif int(order[0]) == 1:
            workflowsteps.sort(lambda x, y: cmp(x.type, y.type))
        elif int(order[0]) == 2:
            workflowsteps.sort(lambda x, y: cmp(x.getTrueId(), y.getTrueId()))
        elif int(order[0]) == 3:
            workflowsteps.sort(lambda x, y: cmp(x.getFalseId(), y.getFalseId()))
        elif int(order[0]) == 4:
            workflowsteps.sort(lambda x, y: cmp(len(x.get("description")), len(y.get("description"))))
        # elif int(order[0]) == 5:
            # workflowstep.sort(lambda x, y: cmp(x.getAccess("read"), y.getAccess("read")))
        # elif int(order[0]) == 6:
            # workflowstep.sort(lambda x, y: cmp(x.getAccess("write"), y.getAccess("write")))
        if int(order[1]) == 1:
            workflowsteps.reverse()
    else:
        workflowsteps.sort(lambda x, y: cmp(x.name.lower(), y.name.lower()))

    v = getAdminStdVars(req)
    v["sortcol"] = pages.OrderColHeader([t(lang(req), "admin_wf_col_{}".format(col)) for col in xrange(1, 8)])
    v["workflow"] = workflow
    v["workflowsteps"] = workflowsteps
    v["pages"] = pages
    v["actfilter"] = actfilter
    v["csrf"] = req.csrf_token.current_token
    return _tal.processTAL(v, file="web/admin/modules/workflows.html", macro="view_step", request=req)

""" edit form for workflowstep for given workflow and given step
    parameter: req=request, wid=workflowid(name), wnid=workflow step id (name), err=error code as integer """


def WorkflowStepDetail(req, wid, wnid, err=0):
    workflow = getWorkflow(wid)
    nodelist = workflow.getSteps().order_by(_Node.name)
    v = getAdminStdVars(req)

    if err == 0 and wnid == "":
        # new workflowstep
        workflowstep = create_update_workflow_step()
        v["orig_name"] = ""
    elif err == -1:
        # update steptype
        if req.values["stepid"]:
            stepname = req.values["nname"]
            workflowstep = create_update_workflow_step(
                    workflow.getStep(stepname),
                    typ=req.values.get("ntype", "workflowstep"),
                    **_aggregate_workflowstep_text_parameters(
                        req.values,
                        workflow.getLanguages(),
                    )
                )
        else:
            err = 0
            workflowstep = create_update_workflow_step(
                    typ=req.values.get("ntype", "workflowstep"),
                    **_aggregate_workflowstep_text_parameters(
                        req.values,
                        workflow.getLanguages(),
                    )
                )
        v["orig_name"] = workflowstep.name

    elif wnid != "" and "nname" not in req.values:
        # edit field
        workflowstep = workflow.getStep(wnid)
        v["orig_name"] = workflowstep.name
    else:
        # error while filling values
        typ = req.values.get("ntype", "workflowstep")
        if typ == "":
            typ = "workflowstep"
        workflowstep = create_update_workflow_step(
                typ=typ,
                **_aggregate_workflowstep_text_parameters(
                    req.values,
                    workflow.getLanguages(),
                )
            )
        v["orig_name"] = req.values["orig_name"]

    if req.values.get("nytype", "") != "":
        workflowstep.setType(req.values.get("nytype", ""))

    v_part = {}
    v_part["fields"] = workflowstep.metaFields(lang(req)) or []
    v_part["node"] = workflowstep
    v_part["hiddenvalues"] = {"wnodeid": workflowstep.name}

    try:
        rule = {
                "read": [r.ruleset_name for r in workflowstep.access_ruleset_assocs.filter_by(ruletype='read')],
                "write": [r.ruleset_name for r in workflowstep.access_ruleset_assocs.filter_by(ruletype='write')],
            }
    except:
        rule = {"read": [], "write": []}

    v["acl_read"] = makeList(req, "read", removeEmptyStrings(rule["read"]), {}, overload=0, type="read")
    v["acl_write"] = makeList(req, "write", removeEmptyStrings(rule["write"]), {}, overload=0, type="write")
    v["editor"] = _tal.processTAL(v_part, file="web/admin/modules/workflows.html", macro="view_editor", request=req)
    v["workflow_id"] = workflow.id
    v["languages"] = filter(None, workflow.get('languages').split(';'))
    v["workflowstep"] = workflowstep
    v["nodelist"] = nodelist
    v["workflowtypes"] = getWorkflowTypes()
    v["error"] = err
    v["update_type"] = req.values.get("ntype", u"")
    v["actpage"] = req.values["actpage"]
    v["csrf"] = req.csrf_token.current_token
    return _tal.processTAL(v, file="web/admin/modules/workflows.html", macro="modify_step", request=req)

""" popup window with image of workflow given by id
    parameter: req=request """


def WorkflowPopup(req):
    path = req.mediatum_contextfree_path[1:].split("/")
    return _tal.processTAL(
            dict(
                id=path[1],
                csrf=req.csrf_token.current_token,
            ),
            file="web/admin/modules/workflows.html",
            macro="view_popup",
            request=req,
        )

""" export workflow-definition (XML) """


def export(req, name):
    return exportWorkflow(name)

""" import definition from file """


def xmlimport(req, filename):
    importWorkflow(filename)
