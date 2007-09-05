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
import tree
import workflows
from acl import AccessData

def edit_workflow(req, ids):
    access = AccessData(req)
    node = tree.getNode(ids[0])

    if not access.hasWriteAccess(node):
        req.writeTAL("edit/edit.html", {}, macro="access_error")
        return

    workflow = None
    workflowstep = None
    ids_without_workflow = []
    not_all_workflows_match = 0
    for id in ids:
        node = tree.getNode(id)
        nodeworkflow = workflows.getNodeWorkflow(node)
        nodeworkflowstep = workflows.getNodeWorkflowStep(node)
        if not nodeworkflow:
            ids_without_workflow += [id]
        if workflow and workflow != nodeworkflow or \
            workflowstep and workflowstep != nodeworkflowstep:
            not_all_workflows_match = 1
        workflow = nodeworkflow
        workflowstep = nodeworkflowstep

    forward_command = req.params.get("form_op",None)
    
    if not_all_workflows_match:
        if forward_command in ["true","false","addworkflow"]:
            req.writeTAL("edit/edit_workflow.html", {}, macro="forward_error")
            return
        # show only nodes without a workflow
        return edit_workflow(req, ids_without_workflow)

    if forward_command:
        if forward_command in ["true", "false"]:
            for id in ids:
                workflowstep = workflows.runWorkflowStep(tree.getNode(id), req.params['form_op'])
        if forward_command == "addworkflow":
            workflow = workflows.getWorkflow(req.params['workflow'])
            for id in ids:
                workflowstep = workflows.setNodeWorkflow(tree.getNode(id), workflow)
        if forward_command == "delete":
            for id in ids:
                node = tree.getNode(id)
                step = workflows.getNodeWorkflowStep(node)
                if step:
                    step.removeChild(node)

        try: del req.params['form_op']
        except: pass

        try: del req.params['workflow']
        except: pass

        return edit_workflow(req, ids)
         
    if workflow:
        print "workflow:",workflow.getName(),workflow.id
    if workflowstep:
        print "workflowstep:",workflowstep.getName(),workflowstep.id

    if workflow == None or workflowstep == None:
        noWorkflow(req, ids)
    else:
        hasWorkflow(req, ids, workflow, workflowstep)

 
def hasWorkflow(req, ids, workflow, workflowstep):
    req.writeTAL("edit/edit_workflow.html",{"link":"?ids="+(",".join(ids))+"&tab=Workflow", "workflow":workflow, "workflowstep":workflowstep}, macro="edit_workflow")     

def noWorkflow(req, ids):
    req.writeTAL("edit/edit_workflow.html",{"link":"?ids="+(",".join(ids))+"&tab=Workflow", "workflows":workflows.getWorkflowList()}, macro="edit_noworkflow")     
   
