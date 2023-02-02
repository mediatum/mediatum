# -*- coding: utf-8 -*-

# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import logging
import flask as _flask
import mediatumtal.tal as _tal

import core.csrfform as _core_csrfform
import core.translation as _core_translation
from .workflow import WorkflowStep, registerStep
from schema.schema import getMetaType
import utils.date as date
from utils.utils import mkKey
from core import Node
from core import db
import schema.schema as _schema
from core.database.postgres.permission import AccessRule, AccessRulesetToRule
from core import UserGroup
import core.nodecache as _nodecache
from core.permission import get_or_add_access_rule

q = db.query

logg = logging.getLogger(__name__)


def register():
    registerStep("workflowstep_start")


def _get_schemas():
    metadatatypes = _nodecache.get_metadatatypes_node()
    for metadatatype in metadatatypes.children.filter(_schema.Metadatatype.a.active == "1").all():
        for datatypename in metadatatype.getDatatypes():
            yield (datatypename, metadatatype.name)


class WorkflowStep_Start(WorkflowStep):

    default_settings = dict(
        schemas=(),
        starthtmltext="",
        allowcontinue=False,
    )

    def show_workflow_step(self, req):
        schemas = frozenset(map(tuple, self.settings["schemas"]))
        redirect = ""
        message = ""

        assert schemas
        # check existence of metadata types listed in the definition of the start node
        if not schemas.issubset(_get_schemas()):
            raise RuntimeError("missing/forbidden schemas: {!r}".format(schemas.difference(_get_schemas())))

        if "workflow_start" in req.params:
            schema = tuple(req.values["selected_schema"].split("/"))
            if schema not in schemas:
                return '<i>{}: {}</i>'.format(schema, _core_translation.translate_in_request("permission_denied", req))

            _core_translation.set_language(req.accept_languages, req.values.get('workflow_language'))
            content_class = Node.get_class_for_typestring(schema[0])
            node = content_class(name=u'', schema=schema[1])
            self.children.append(node)

            # create user group named '_workflow' if it doesn't exist
            workflow_group = q(UserGroup).filter_by(name=u'_workflow').scalar()
            if workflow_group is None:
                workflow_group = UserGroup(name=u'_workflow', description=u'internal dummy group for nodes in workflows')
                db.session.add(workflow_group)

            # create access rule with '_workflow' user group
            workflow_rule = get_or_add_access_rule(group_ids=[workflow_group.id])

            special_access_ruleset = node.get_or_add_special_access_ruleset(ruletype=u'read')
            special_access_ruleset.rule_assocs.append(AccessRulesetToRule(rule=workflow_rule))

            node.set("creator", "workflow-" + self.parents[0].name)
            node.set("creationtime", date.format_date())
            node.set("system.wflanguage", req.params.get('workflow_language', _flask.session.get('language')))
            node.set("key", mkKey())
            node.set("system.key", node.get("key"))  # initial key identifier
            _flask.session["key"] = node.get("key")
            db.session.commit()
            return self.forwardAndShow(node, True, req)

        elif "workflow_start_auth" in req.params:  # auth node by id and key
            try:
                node = q(Node).get(req.params.get('nodeid'))

                # startkey, but protected
                if node.get('system.key') == req.params.get('nodekey') and node.get('key') != req.params.get('nodekey'):
                    message = "workflow_start_err_protected"
                elif node.get('key') == req.params.get('nodekey'):
                    redirect = "/pnode?id=%s&key=%s" % (node.id, node.get('key'))
                else:
                    message = "workflow_start_err_wrongkey"
            except:
                logg.exception("exception in workflow step start (workflow_start_auth)")
                message = "workflow_start_err_wrongkey"
                db.session.rollback()

        return _tal.processTAL(
                dict(
                    types=sorted((getMetaType(s[1]).getLongName(), '/'.join(s)) for s in schemas),
                    id=self.id,
                    starthtmltext=self.settings['starthtmltext'],
                    languages=self.parents[0].getLanguages(),
                    currentlang=_core_translation.set_language(req.accept_languages),
                    redirect=redirect,
                    message=message,
                    allowcontinue=self.settings['allowcontinue'],
                    csrf=_core_csrfform.get_token(),
                ),
                file="workflow/start.html",
                macro="workflow_start",
                request=req,
            )

    def admin_settings_get_html_form(self, req):
        return _tal.processTAL(
            dict(
                allowcontinue=self.settings["allowcontinue"],
                schemas=map(tuple, self.settings["schemas"]),
                starthtmltext=self.settings["starthtmltext"],
                permitted_schemas=sorted(_get_schemas()),
               ),
            file="workflow/start.html",
            macro="workflow_step_type_config",
            request=req,
           )

    def admin_settings_save_form_data(self, data):
        schemas = data.getlist("schemas")
        data = data.to_dict()
        data["allowcontinue"] = bool(data.get("allowcontinue"))
        data["schemas"] = tuple(s.split("/") for s in schemas)
        assert frozenset(data) == frozenset(("schemas", "starthtmltext", "allowcontinue"))
        self.settings = data
        db.session.commit()
