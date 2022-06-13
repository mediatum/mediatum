# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import itertools as _itertools
import pkgutil
import importlib
import flask as _flask

import core.config as config
import mediatumtal.tal as _tal

from utils.utils import *
from core.xmlnode import getNodeXML, readNodeXML

import utils.date as date
import core.csrfform as _core_csrfform
import core.translation as _core_translation

from core.users import user_from_session as _user_from_session
from core.postgres import check_type_arg
from core.database.postgres.permission import NodeToAccessRuleset
import core.nodecache as _nodecache

from utils.locks import named_lock as _named_lock

from core import db
from core import Node
from utils.url import build_url_from_path_and_params as _build_url_from_path_and_params


q = db.query
logg = logging.getLogger(__name__)


def getWorkflowList():
    return _nodecache.get_workflows_node().children.all()


def getWorkflow(name):
    if name.isdigit():
        return q(Workflow).get(name)
    else:
        return _nodecache.get_workflows_node().children.filter_by(name=name).one()


def addWorkflow(name, description):
    node = Workflow(name=name, type=u'workflow')
    _nodecache.get_workflows_node().children.append(node)
    node.set("description", description)
    db.session.commit()

    return node


def updateWorkflow(name, description, nameattribute="", origname="", writeaccess=""):
    if origname == "":
        if _nodecache.get_workflows_node().children.filter_by(name=name).scalar() is None:
            w = addWorkflow(name, description)
        else:
            w = _nodecache.get_workflows_node().children.filter_by(name=name).one()
    else:
        w = _nodecache.get_workflows_node().children.filter_by(name=origname).one()
        w.name = name
    w.set("description", description)
    w.display_name_attribute = nameattribute

    # TODO: is this part necessary?
    if not writeaccess:
        for r in w.access_ruleset_assocs.filter_by(ruletype=u'write'):
            db.session.delete(r)
    else:
        w.access_ruleset_assocs.append(NodeToAccessRuleset(ruleset_name=writeaccess, ruletype=u'write'))
    db.session.commit()

    return w


def deleteWorkflow(id):
    workflows = _nodecache.get_workflows_node()
    w = workflows.children.filter_by(name=id).one()
    workflows.children.remove(w)
    db.session.commit()


def inheritWorkflowRights(name, type):
    w = getWorkflow(name)
    ac = w.access_ruleset_assocs.filter_by(ruletype=type)
    for step in w.children:
        for r in ac:
            if step.access_ruleset_assocs.filter_by(ruleset_name=r.ruleset_name, ruletype=type).first() is None:
                step.access_ruleset_assocs.append(NodeToAccessRuleset(ruleset_name=r.ruleset_name, ruletype=type))
    db.session.commit()


def getNodeWorkflow(node):
    for p in node.parents:
        for p2 in p.parents:
            if p2.type == "workflow":
                return p2
    return None


def getNodeWorkflowStep(node):
    workflow = getNodeWorkflow(node)
    if workflow is None:
        return None
    steps = [n.id for n in workflow.getSteps()]
    for p in node.parents:
        if p.id in steps:
            return p
    return None

# execute step operation and set node step


def runWorkflowStep(node, op, forward=True):
    workflow = getNodeWorkflow(node)
    workflowstep = getNodeWorkflowStep(node)

    if workflowstep is None:
        return

    if forward:
        newstep = None
        if op == "true":
            newstep = workflow.getStep(workflowstep.getTrueId())
        else:
            newstep = workflow.getStep(workflowstep.getFalseId())

        workflowstep.children.remove(node)
        newstep.children.append(node)
        db.session.commit()
    else:
        newstep = workflowstep
    newstep.runAction(node, op)
    logg.info('workflow run action "%s" (op="%s") for node %s', newstep.name, op, node.id)
    return getNodeWorkflowStep(node)

# set workflow for node


def setNodeWorkflow(node, workflow):
    """XXX: unused?"""
    start = workflow.getStartNode()
    start.children.append(node)
    start.runAction(node, True)
    db.session.commit()
    return getNodeWorkflowStep(node)


def create_update_workflow_step(
        step=None,
        name="",
        typ="workflowstep",
        trueid="",
        falseid="",
        truelabel="",
        falselabel="",
        pretext="",
        posttext="",
        comment="",
        adminstep="",
       ):
    """
    :param step: update workflowstep if it is not None
    :return: updated or created workflowstep
    """
    if step is None:
        step = WorkflowStep(name)
        step.set_class(typ)
    else:
        if step.name != name:
            # the button targets of the other workflow steps are adjusted for update case
            for node in step.parents.one().children:
                if node.get("truestep") == step.name:
                    node.set("truestep", name)
                if node.get("falsestep") == step.name:
                    node.set("falsestep", name)
        if step.type != typ:
            # if the type has changed every access to n after db.session.comm() leads to the error:
            # ObjectDeletedError: Instance '' has been deleted, or its row is otherwise not present.
            # Workarround: create a temporary workflowstep n_new with the new type and set the id to the same id of n
            stepid = step.id  # save n.id, after db.session.commit() n.id is no longer accessible
            step.type = typ
            db.session.commit()
            step = WorkflowStep(typ)
            step.set_class(typ)
            step.id = stepid
    step.name = name
    step.type = typ
    step.set("truestep", trueid)
    step.set("falsestep", falseid)
    step.set("truelabel", truelabel)
    step.set("falselabel", falselabel)
    step.set("pretext", pretext)
    step.set("posttext", posttext)
    step.set("comment", comment)
    step.set("adminstep", adminstep)

    db.session.commit()

    return step


def deleteWorkflowStep(workflowid, stepid):
    workflows = _nodecache.get_workflows_node()
    wf = workflows.children.filter_by(name=workflowid).one()
    ws = wf.children.filter_by(name=stepid).one()
    wf.children.remove(ws)
    db.session.commit()

workflowtypes = {}


def registerStep(nodename):
    name = nodename
    if "_" in nodename:
        name = nodename[nodename.index("_") + 1:]
    workflowtypes[nodename] = name


def registerWorkflowStep(nodename, cls):
    name = nodename
    if "_" in nodename:
        name = nodename[nodename.index("_") + 1:]
    workflowtypes[nodename] = name

    _core_translation.addLabels(cls.getLabels())


def getWorkflowTypes():
    return workflowtypes

def workflowSearch(nodes, text):
    text = text.strip()
    if text == "":
        return []

    ret = []
    for node in filter(lambda x: x.type == 'workflow', nodes):
        for n in node.getSteps("write"):
            for c in n.children:
                if text == "*":
                    ret += [c]
                elif isNumeric(text):
                    if c.id == int(text):
                        ret += [c]
                else:
                    if "|".join([f[1].lower() for f in c.attrs.items()]).find(text.lower()) >= 0:
                        ret += [c]

    return ret


def formatItemDate(d):
    try:
        return date.format_date(date.parse_date(d), 'dd.mm.yyyy HH:MM:SS')
    except:
        logg.exception("exception in formatItemDate, return empty string")
        return ""


""" export workflow definition """


def exportWorkflow(name):
    if name == "all":
        return getNodeXML(_nodecache.get_workflows_node())
    else:
        return getNodeXML(getWorkflow(name))


""" import workflow from file """


def importWorkflow(filename):
    n = readNodeXML(filename)
    importlist = list()

    if n.type == "workflow":
        importlist.append(n)
    elif n.type == "workflows":
        for ch in n.children:
            importlist.append(ch)
    workflows = _nodecache.get_workflows_node()
    for w in importlist:
        w.name = "import_" + w.name
        workflows.children.append(w)
    db.session.commit()


@check_type_arg
class Workflows(Node):

    def show_node_big(self, req, *args):
        # style name is ignored
        template = "workflow/workflow.html"
        macro= "workflowlist"
        list = []
        for workflow in getWorkflowList():
            if workflow.children.filter_write_access().first() is not None:
                list += [workflow]
        return _tal.processTAL(
                dict(
                    list=list,
                    search=req.values.get("workflow_search", ""),
                    items=workflowSearch(list, req.values.get("workflow_search", "")),
                    getStep=getNodeWorkflowStep,
                    format_date=formatItemDate,
                    csrf=_core_csrfform.get_token(),
                ),
                file=template,
                macro=macro,
                request=req,
            )

    @classmethod
    def isContainer(cls):
        return 1

    def isSystemType(node):
        return 1

    def getLabel(self, lang=None):
        return self.name


@check_type_arg
class Workflow(Node):

    def show_node_big(self, req, *args): 
        template = "workflow/workflow.html"
        macro = "object_list"
        if self.children.filter_write_access().first() is None:
            return '<i>' + _core_translation.t(_core_translation.set_language(req.accept_languages), "permission_denied") + '</i>'
        return _tal.processTAL(
                dict(
                    workflow=self,
                    search=req.values.get("workflow_search", ""),
                    items=workflowSearch([self], req.values.get("workflow_search", "")),
                    getStep=getNodeWorkflowStep,
                    format_date=formatItemDate,
                    csrf=_core_csrfform.get_token(),
                ),
                file=template,
                macro=macro,
                request=req,
            )

    def getId(self):
        return self.name

    def setId(self, i):
        self.setName(i)

    def getLink(self):
        return '?id=' + self.id

    def show_node_image(node):
        return '<img border="0" src="/img/directory.png">'

    def show_node_text(node, words=None):
        return ""

    def getLabel(self, lang=None):
        return self.name

    @classmethod
    def isContainer(cls):
        return 1

    def isSystemType(node):
        return 1

    @property
    def display_name_attribute(self):
        return self.get("display_name_attribute")

    @display_name_attribute.setter
    def display_name_attribute(self, value):
        self.set("display_name_attribute", value)

    def getLanguages(node):
        if node.get('languages') != '':
            return node.get('languages').split(';')
        return []

    def getDescription(self):
        return self.get("description")

    def setDescription(self, d):
        self.set("description", d)

    def getSteps(self, accesstype=''):
        steps = self.children
        if accesstype:
            return [s for s in steps if s.has_access(accesstype=accesstype)]
        else:
            return steps

    def getNode(self, type):
        raise Exception()

    def getStartNode(self):
        followers = {}
        for step in self.children:
            if step.getTrueId():
                followers[step.getTrueId()] = None
            if step.getFalseId():
                followers[step.getFalseId()] = None
        # Start nodes have no predecessor (= are not follower of any node)
        # XXX: no check if multiple start nodes are present!
        for step in self.children:
            if step.name not in followers:
                return step
        return None  # circular workflow- shouldn't happen

    def getStep(self, name, test_only=False):
        if name.isdigit():
            return q(Node).get(name)
        else:
            if test_only:
                return self.children.filter_by(name=name).scalar()
            return self.children.filter_by(name=name).one()

    def getNodeList(self):
        list = []
        for step in self.getSteps():
            list += step.children
        return list

    def addStep(self, step):
        self.children.append(step)
        db.session.commit()
        return step


workflow_lock = _named_lock('workflow')


@check_type_arg
class WorkflowStep(Node):

    def set_class(self, type):
        # set the correct WorkflowStep-class e.g. WorkflowStep_Publish
        self.__class__ = self.get_class_for_typestring(type)

    def getId(self):
        return self.name

    def show_node_big(self, req, *args):
        template = "workflow/workflow.html"
        macro = "object_step"

        # the workflow operations (node forwarding, key assignment,
        # parent node handling) are highly non-reentrant, so protect
        # everything with a global lock
        global workflow_lock

        with workflow_lock:
            # stop caching

            key = req.values.get("key", _flask.session.get("key", ""))
            _flask.session["key"] = key

            if "obj" in req.params:
                nodes = [q(Node).get(int(id)) for id in req.values.getlist('obj')]

                for node in nodes:
                    if not self.has_write_access() and \
                            (key != node.get("key")):  # no permission

                        link = '(' + self.name + ')'
                        try:
                            return _tal.processTAL(
                                    dict(
                                        node=node,
                                        link=link,
                                        email=config.get("email.workflow"),
                                        csrf=_core_csrfform.get_token(),
                                    ),
                                    file=template,
                                    macro=macro,
                                    request=req,
                                )
                        except:
                            logg.exception("exception in show_node_big, ignoring")
                            return ""

                if 'action' in req.values:
                    if self.has_write_access():
                        if req.values.get('action') == 'delete':
                            for node in nodes:
                                for parent in node.parents:
                                    parent.children.remove(node)
                        elif req.values.get('action').startswith('move_'):
                            step = q(Node).get(req.values.get('action').replace('move_', ''))
                            for node in nodes:
                                for parent in node.parents:
                                    parent.children.remove(node)
                                step.children.append(node)
                    db.session.commit()
                    return self.show_workflow_step(req)

                else:
                    node = nodes[0]

                if self in node.parents:
                    # set correct language for workflow for guest user only
                    user = _user_from_session()
                    if node.get('key') == node.get('system.key') and user.is_anonymous:
                        _core_translation.set_language(req.accept_languages, node.get('system.wflanguage'))

                    link = _build_url_from_path_and_params("/mask", {"id": self.id})
                    if "forcetrue" in req.values:
                        return self.forwardAndShow(node, True, req, link=link)
                    if "forcefalse" in req.values:
                        return self.forwardAndShow(node, False, req, link=link)

                    return self.show_workflow_node(node, req)
                else:
                    return self.show_workflow_notexist(node, req)
            else:
                return self.show_workflow_step(req)

    @classmethod
    def isContainer(cls):
        # inhibit several content enrichment features
        return 1

    def isSystemType(self):
        return 1

    def show_workflow_notexist(self, node, req, template="workflow/workflow.html", macro="workflow_node"):
        step = getNodeWorkflowStep(node)
        link = ""
        if step:
            link = '/mask?id=%s&obj=%s' % (step.id, node.id)
            return '<script language="javascript">document.location.href = "%s";</script> <a href="%s">%s</a>' % (link, link, step.name)
        else:
            return '<i>{}</i>'.format(_core_translation.t(_core_translation.set_language(req.accept_languages), "permission_denied"))

    def show_workflow_node(self, node, req):
        if "gotrue" in req.values:
            return self.forwardAndShow(node, True, req)
        if "gofalse" in req.values:
            return self.forwardAndShow(node, False, req)

        # to be overloaded
        return _tal.processTAL({"node": node, "name": self.name}, file="workflow/workflow.html", macro="workflow_node", request=req)

    def show_workflow_step(self, req):
        if not self.has_write_access():
            return '<i>{}</i>'.format(_core_translation.t(_core_translation.set_language(req.accept_languages), "permission_denied"))
        c = []
        display_name_attr = self.parents[0].display_name_attribute
        i = 0
        for item in self.children.prefetch_attrs():
            c.append({"id": unicode(item.id), "creationtime": date.format_date(
                date.parse_date(item.get('creationtime')), 'dd.mm.yyyy HH:MM:SS')})
            if display_name_attr:
                c[i]["name"] = item.get(display_name_attr)
            else:
                c[i]["name"] = item.name
            i += 1
        c.sort(lambda x, y: cmp(x['name'], y['name']))
        nodelink = "/mask?id={}&obj=".format(self.id)

        def mk_row(child):
            context = dict(
                child_id=child["id"],
                child_creationtime=child["creationtime"],
                child_name=child["name"],
                step=self,
                nodelink=nodelink,
            )
            return _tal.processTAL(context,
                                   file="workflow/workflow.html",
                                   macro="workflow_show_table",
                                   request=req,
                                   )

        context = dict(
            len_children=len(c),
            table="".join(_itertools.imap(mk_row, c)),
            workflow=self.parents[0],
            step=self,
            nodelink=nodelink,
            csrf=_core_csrfform.get_token(),
        )
        return _tal.processTAL(context,
                               file="workflow/workflow.html",
                               macro="workflow_show",
                               request=req,
                               )

    def show_node_image(node):
        return '<img border="0" src="/img/directory.png">'

    def show_node_text(node, req, context):
        return ""

    def getLabel(self, lang=None):
        return self.name

    def getLink(self):
        return "/mask?id=" + unicode(self.id)

    def isAdminStep(self):
        if self.get("adminstep") == "1":
            return 1
        return 0

    def runAction(self, node, op=""):
        if self.getTrueId() == '':
            logg.error("No Workflow action defined for workflowstep %s (op=%s)", self.getId(), op)

    def forward(self, node, op, forward=True):
        op_str = "true" if op else "false"
        return runWorkflowStep(node, op_str, forward)

    def forwardAndShow(self, node, op, req, link=None, data=None, forward=True):
        newnode = self.forward(node, op, forward)

        if newnode is None:
            return _tal.processTAL({"node": node}, file="workflow/workflow.html", macro="workflow_forward", request=req)

        if link is None:
            context = {"id": newnode.id, "obj": node.id}
            if data and isinstance(data, type({})):
                for k in data:
                    if k not in context:
                        context[k] = data[k]
                    else:
                        logg.warning("workflow '%s', step '%s', node %s: ignored data key '%s' (value='%s')",
                                     getNodeWorkflow(node).name, getNodeWorkflowStep(node).name, node.id, k, data[k])

            newloc = _build_url_from_path_and_params("/mask", context)
        else:
            newloc = link
        redirect = 1
        if redirect == 0:
            return _tal.processTAL(context, file="workflow/workflow.html", macro="workflow_forward2", request=req)
        else:
            if config.get("config.ssh", "") == "yes":
                if not newloc.lower().startswith("https:"):
                    newloc = "https://" + config.get("host.name") + newloc.replace("http://" + config.get("host.name"), "")
            return '<script language="javascript">document.location.href = "%s";</script>' % newloc

    def getTrueId(self):
        """XXX: misleading name: returns name, not node id!"""
        return self.get("truestep")

    def getFalseId(self):
        """XXX: misleading name: returns name, not node id!"""
        return self.get("falsestep")

    def getTrueLabel(self, language=""):
        value = self.get("truelabel")
        for line in value.split('\n'):
            if line.startswith(language + ':'):
                return line.replace(language + ':', '')
        value = value.split('\n')[0]  # use first language
        for lang in config.languages:
            value = value.replace('%s:' % (lang), '')
        return value.strip()

    def getFalseLabel(self, language=""):
        value = self.get("falselabel")
        for line in value.split('\n'):
            if line.startswith(language + ':'):
                return line.replace(language + ':', '')
        value = value.split('\n')[0]  # use first language
        for lang in config.languages:
            value = value.replace('%s:' % (lang), '')
        return value.strip()

    def getTrueFunction(self):
        return self.get("truefunction")

    def getFalseFunction(self):
        return self.get("falsefunction")

    def getPreText(self, language=""):
        value = self.get("pretext")
        for line in value.split('\n'):
            if line.startswith(language + ':'):
                return line.replace(language + ':', '')
        return value

    def getPostText(self, language=""):
        value = self.get("posttext")
        for line in value.split('\n'):
            if line.startswith(language + ':'):
                return line.replace(language + ':', '')
        return value

    def getComment(self):
        return self.get("comment")

    def metaFields(self, lang=None):
        return list()

    def tableRowButtons(self, node):
        if node.get('system.key') == node.get('key'):
            # user has permission -> use users language
            return _tal.getTAL("workflow/workflow.html",
                              {'node': node,
                               'wfstep': self,
                               'lang': node.get('system.wflanguage')},
                              macro="workflow_buttons",
                              language=node.get('system.wflanguage'))
        else:
            # use standard language of request
            return _tal.getTAL(
                    "workflow/workflow.html",
                    dict(node=node, wfstep=self, lang=_core_translation.getDefaultLanguage()),
                    macro="workflow_buttons",
                    language=_core_translation.getDefaultLanguage(),
                )

    def getTypeName(self):
        return self.name

    def getShortName(self, req):
        l = _core_translation.set_language(req.accept_languages)
        if self.get('shortstepname_' + l) != "":
            return self.get('shortstepname_' + l)
        elif self.get('shortstepname') != "":
            return self.get('shortstepname')
        else:
            return ""

    def setShortName(self, value, lang=""):
        if lang != "":
            self.set('shortstepname_' + lang, value.strip())
        else:
            self.set('shortstepname', value.strip())


def register():
    # tree.registerNodeClass("workflows", Workflows)
    # tree.registerNodeClass("workflow", Workflow)
    # tree.registerNodeClass("workflowstep", WorkflowStep)

    # run register method of step types
    path = os.path.dirname(__file__)
    for _, name, _ in pkgutil.iter_modules([path]):
        if name != "workflow":
            m = importlib.import_module("workflow." + name)
            if hasattr(m, 'register'):
                logg.debug("registering workflow step '%s'", name)
                m.register()
