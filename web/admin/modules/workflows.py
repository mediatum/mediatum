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
import re
import sys
import traceback

import core.config as config

from workflow.workflow import Workflow, getWorkflowList, getWorkflow, updateWorkflow, addWorkflow, deleteWorkflow, inheritWorkflowRights, getWorkflowTypes, updateWorkflowStep, createWorkflowStep, deleteWorkflowStep, exportWorkflow, importWorkflow
from web.admin.adminutils import Overview, getAdminStdVars, getFilter, getSortCol
from schema.schema import parseEditorData
from web.common.acl_web import makeList
from utils.utils import removeEmptyStrings
from core.translation import t, lang
from core import db
from core.database.postgres.permission import NodeToAccessRuleset

logg = logging.getLogger(__name__)


def getInformation():
    return{"version": "1.0"}

""" standard validator to execute correct method """


def validate(req, op):
    path = req.path[1:].split("/")
    if len(path) == 3 and path[2] == "overview":
        return WorkflowPopup(req)

    if "file" in req.params and hasattr(req.params["file"], "filesize") and req.params["file"].filesize > 0:
        # import scheme from xml-file
        importfile = req.params.get("file")
        if importfile.tempname != "":
            xmlimport(req, importfile.tempname)

    if req.params.get("form_op", "") == "update":
        return WorkflowStepDetail(req, req.params.get("parent"), req.params.get("nname"), -1)

    try:

        if req.params.get("acttype", "workflow") == "workflow":
            # workflow section
            for key in req.params.keys():
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
                    #req.params["detailof"] = key[11:-2]
                    return WorkflowStepList(req, key[11:-2])

            if "form_op" in req.params.keys():
                if req.params.get("form_op", "") == "cancel":
                    return view(req)

                if req.params.get("name", "") == "":
                    return WorkflowDetail(req, req.params.get("id", ""), 1)  # no name was given

                if req.params.get("form_op") == "save_new":
                    # save workflow values
                    addWorkflow(req.params.get("name", ""), req.params.get("description"))
                elif req.params.get("form_op") == "save_edit":
                    # save workflow values
                    updateWorkflow(req.params.get("name", ""), req.params.get("description"),
                                   req.params.get("name_attr"), req.params.get("orig_name"))

                wf = getWorkflow(req.params.get("name"))
                if wf:
                    if "wf_language" in req.params:
                        wf.set('languages', req.params.get('wf_language'))
                    else:
                        if wf.get('languages'):
                            del wf.attrs['languages']

                    for r in wf.access_ruleset_assocs.filter_by(ruletype=u'read'):
                        db.session.delete(r)

                    for key in req.params.keys():
                        if key.startswith("left_read"):
                            for r in req.params.get(key).split(';'):
                                wf.access_ruleset_assocs.append(NodeToAccessRuleset(ruleset_name=r, ruletype=key[9:]))
                            break

                    for r in wf.access_ruleset_assocs.filter_by(ruletype=u'write'):
                        db.session.delete(r)

                    for key in req.params.keys():
                        if key.startswith("left_write"):
                            for r in req.params.get(key).split(';'):
                                wf.access_ruleset_assocs.append(NodeToAccessRuleset(ruleset_name=r, ruletype=key[10:]))
                            break

                    # check for right inheritance
                    if "write_inherit" in req.params:
                        inheritWorkflowRights(req.params.get("name", ""), "write")
                    if "read_inherit" in req.params:
                        inheritWorkflowRights(req.params.get("name", ""), "read")
                    db.session.commit()

        else:
            # workflowstep section
            for key in req.params.keys():
                if key.startswith("newdetail_"):
                    # create new workflow
                    return WorkflowStepDetail(req, req.params.get("parent"), "")
                elif key.startswith("editdetail_"):
                    # edit workflowstep
                    return WorkflowStepDetail(req, req.params.get("parent"), key[11:-2].split("|")[1])

                elif key.startswith("deletedetail_"):
                    # delete workflow step id: deletedetail_[workflowid]|[stepid]
                    deleteWorkflowStep(key[13:-2].split("|")[0], key[13:-2].split("|")[1])
                    break

            if "form_op" in req.params.keys():
                if req.params.get("form_op", "") == "cancel":
                    return WorkflowStepList(req, req.params.get("parent"))

                if req.params.get("nname", "") == "":  # no Name was given
                    return WorkflowStepDetail(req, req.params.get("parent"), req.params.get("stepid", ""), 1)

                if req.params.get("form_op", "") == "save_newdetail":
                    # save workflowstep values -> create
                    wnode = createWorkflowStep(
                        name=req.params.get(
                            "nname", ""), type=req.params.get(
                            "ntype", ""), trueid=req.params.get(
                            "ntrueid", ""), falseid=req.params.get(
                            "nfalseid", ""), truelabel=req.params.get(
                            "ntruelabel", ""), falselabel=req.params.get(
                            "nfalselabel", ""), comment=req.params.get(
                                "ncomment", ""), adminstep=req.params.get(
                                    "adminstep", ""))
                    getWorkflow(req.params.get("parent")).addStep(wnode)

                elif req.params.get("form_op") == "save_editdetail":
                    # update workflowstep
                    wf = getWorkflow(req.params.get("parent"))
                    truelabel = ''
                    falselabel = ''
                    for language in wf.getLanguages():
                        truelabel += '%s:%s\n' % (language, req.params.get('%s.ntruelabel' % language))
                        falselabel += '%s:%s\n' % (language, req.params.get('%s.nfalselabel' % language))
                    if truelabel == '':
                        truelabel = req.params.get("ntruelabel", "")
                    if falselabel == '':
                        falselabel = req.params.get("nfalselabel", "")
                    sidebartext = ''
                    pretext = ''
                    posttext = ''

                    if len(wf.getLanguages()) > 1:
                        for language in wf.getLanguages():
                            sidebartext += '%s:%s\n' % (language, req.params.get('%s.nsidebartext' % language).replace('\n', ''))
                            pretext += '%s:%s\n' % (language, req.params.get('%s.npretext' % language).replace('\n', ''))
                            posttext += '%s:%s\n' % (language, req.params.get('%s.nposttext' % language).replace('\n', ''))

                    if sidebartext == '':
                        sidebartext = req.params.get("nsidebartext", "").replace('\n', '')
                    if pretext == '':
                        pretext = req.params.get("npretext", "").replace('\n', '')
                    if posttext == '':
                        posttext = req.params.get("nposttext", "").replace('\n', '')

                    wnode = updateWorkflowStep(
                        wf, oldname=req.params.get(
                            "orig_name", ""), newname=req.params.get(
                            "nname", ""), type=req.params.get(
                            "ntype", ""), trueid=req.params.get(
                            "ntrueid", ""), falseid=req.params.get(
                            "nfalseid", ""), truelabel=truelabel, falselabel=falselabel, sidebartext=sidebartext, pretext=pretext, posttext=posttext, comment=req.params.get(
                            "ncomment", ""), adminstep=req.params.get(
                                "adminstep", ""))

                try:
                    wfs = getWorkflow(req.params.get("parent")).getStep(req.params.get("orig_name", ""))
                except:
                    wfs = getWorkflow(req.params.get("parent")).getStep(req.params.get("nname", ""))
                if wfs:
                    for r in wfs.access_ruleset_assocs.filter_by(ruletype=u'read'):
                        db.session.delete(r)

                    for key in req.params.keys():
                        if key.startswith("left_read"):
                            for r in req.params.get(key).split(';'):
                                wfs.access_ruleset_assocs.append(NodeToAccessRuleset(ruleset_name=r, ruletype=key[9:]))
                            break

                    for r in wfs.access_ruleset_assocs.filter_by(ruletype=u'write'):
                        db.session.delete(r)

                    for key in req.params.keys():
                        if key.startswith("left_write"):
                            for r in req.params.get(key).split(';'):
                                wfs.access_ruleset_assocs.append(NodeToAccessRuleset(ruleset_name=r, ruletype=key[10:]))
                            break
                    db.session.commit()

                if "metaDataEditor" in req.params.keys():
                    parseEditorData(req, wnode)

            return WorkflowStepList(req, req.params.get("parent"))

        return view(req)
    except:
        logg.exception("exception in validate")


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
    v["sortcol"] = pages.OrderColHeader(
        [t(lang(req), "admin_wf_col_1"), t(lang(req), "admin_wf_col_2"), t(lang(req), "admin_wf_col_3"), t(lang(req), "admin_wf_col_4")])
    v["workflows"] = workflows
    v["pages"] = pages
    v["actfilter"] = actfilter

    return req.getTAL("web/admin/modules/workflows.html", v, macro="view")

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
        workflow.name = req.params.get("name", "")
        workflow.set("description", req.params.get("description", ""))
        #workflow.setAccess("write", req.params.get("writeaccess", ""))
        v["original_name"] = req.params.get("orig_name", "")
        workflow.id = req.params.get("id")
        db.session.commit()

    try:
        rule = {"read": [r.ruleset_name for r in workflow.access_ruleset_assocs.filter_by(ruletype='read')],
                "write": [r.ruleset_name for r in workflow.access_ruleset_assocs.filter_by(ruletype='write')]}
    except:
        rule = {"read": [], "write": []}

    v["acl_read"] = makeList(req, "read", removeEmptyStrings(rule["read"]), {}, overload=0, type="read")
    v["acl_write"] = makeList(req, "write", removeEmptyStrings(rule["write"]), {}, overload=0, type="write")
    v["workflow"] = workflow
    v["languages"] = config.languages
    v["error"] = err
    v["actpage"] = req.params.get("actpage")
    return req.getTAL("web/admin/modules/workflows.html", v, macro="modify")

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
    v["sortcol"] = pages.OrderColHeader(
        [
            t(
                lang(req), "admin_wfstep_col_1"), t(
                lang(req), "admin_wfstep_col_2"), t(
                    lang(req), "admin_wfstep_col_3"), t(
                        lang(req), "admin_wfstep_col_4"), t(
                            lang(req), "admin_wfstep_col_5"), t(
                                lang(req), "admin_wfstep_col_6"), t(
                                    lang(req), "admin_wfstep_col_7")])
    v["workflow"] = workflow
    v["workflowsteps"] = workflowsteps
    v["pages"] = pages
    v["actfilter"] = actfilter
    return req.getTAL("web/admin/modules/workflows.html", v, macro="view_step")

""" edit form for workflowstep for given workflow and given step
    parameter: req=request, wid=workflowid(name), wnid=workflow step id (name), err=error code as integer """


def WorkflowStepDetail(req, wid, wnid, err=0):
    workflow = getWorkflow(wid)
    nodelist = workflow.getSteps()
    v = getAdminStdVars(req)

    if err == 0 and wnid == "":
        # new workflowstep
        workflowstep = createWorkflowStep(name="", trueid="", falseid="", truelabel="", falselabel="", comment="")
        workflowstep.set("id",  "")
        v["orig_name"] = req.params.get("orig_name", "")

    elif err == -1:
        # update steptype
        if req.params.get("stepid", ""):
            workflowstep = updateWorkflowStep(
                workflow, oldname=req.params.get(
                    "nname", ""), newname=req.params.get(
                    "nname", ""), type=req.params.get(
                    "ntype", "workflowstep"), trueid=req.params.get(
                    "ntrueid", ""), falseid=req.params.get(
                        "nfalseid", ""), truelabel=req.params.get(
                            "ntruelabel", ""), falselabel=req.params.get(
                                "nfalselabel", ""), comment=req.params.get(
                                    "ncomment", ""))
        else:
            err = 0
            workflowstep = createWorkflowStep(
                name=req.params.get(
                    "nname", ""), type=req.params.get(
                    "ntype", "workflowstep"), trueid=req.params.get(
                    "ntrueid", ""), falseid=req.params.get(
                    "nfalseid", ""), truelabel=req.params.get(
                        "ntruelabel", ""), falselabel=req.params.get(
                            "nfalselabel", ""), comment=req.params.get(
                                "ncomment", ""))
            if req.params.get("wnid", "") == "":
                workflowstep.set("id",  "")
        v["orig_name"] = workflowstep.name

    elif wnid != "" and req.params.get("nname") != "":
        # edit field
        workflowstep = workflow.getStep(wnid)
        v["orig_name"] = workflowstep.name
    else:
        # error while filling values
        type = req.params.get("ntype", "workflowstep")
        if type == "":
            type = "workflowstep"
        workflowstep = createWorkflowStep(
            name=req.params.get(
                "nname", ""), type=type, trueid=req.params.get(
                "ntrueid", ""), falseid=req.params.get(
                "nfalseid", ""), truelabel=req.params.get(
                    "ntruelabel", ""), falselabel=req.params.get(
                        "nfalselabel", ""), comment=req.params.get(
                            "ncomment", ""))
        v["orig_name"] = req.params.get("orig_name", "")

    if req.params.get("nytype", "") != "":
        workflowstep.setType(req.params.get("nytype", ""))

    v_part = {}
    v_part["fields"] = workflowstep.metaFields(lang(req)) or []
    v_part["node"] = workflowstep
    v_part["hiddenvalues"] = {"wnodeid": workflowstep.name}

    try:
        rule = {"read": [r.ruleset_name for r in workflowstep.access_ruleset_assocs.filter_by(ruletype='read')],
                "write": [r.ruleset_name for r in workflowstep.access_ruleset_assocs.filter_by(ruletype='write')]}
    except:
        rule = {"read": [], "write": []}

    v["acl_read"] = makeList(req, "read", removeEmptyStrings(rule["read"]), {}, overload=0, type="read")
    v["acl_write"] = makeList(req, "write", removeEmptyStrings(rule["write"]), {}, overload=0, type="write")
    v["editor"] = req.getTAL("web/admin/modules/workflows.html", v_part, macro="view_editor")
    v["workflow"] = workflow
    v["workflowstep"] = workflowstep
    v["nodelist"] = nodelist
    v["workflowtypes"] = getWorkflowTypes()
    v["error"] = err
    v["update_type"] = req.params.get("ntype", u"")
    v["actpage"] = req.params.get("actpage")
    return req.getTAL("web/admin/modules/workflows.html", v, macro="modify_step")

""" popup window with image of workflow given by id
    parameter: req=request """


def WorkflowPopup(req):
    path = req.path[1:].split("/")
    return req.getTAL("web/admin/modules/workflows.html", {"id": path[1]}, macro="view_popup")

""" export workflow-definition (XML) """


def export(req, name):
    return exportWorkflow(name)

""" import definition from file """


def xmlimport(req, filename):
    importWorkflow(filename)
