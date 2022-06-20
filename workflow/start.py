# -*- coding: utf-8 -*-

# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import logging
import flask as _flask
import mediatumtal.tal as _tal

import core.config as config
import core.csrfform as _core_csrfform
import core.translation as _core_translation
from .workflow import WorkflowStep, registerStep
from schema.schema import getMetaType
import utils.date as date
from utils.utils import mkKey
from core import Node
from core import db
from schema.schema import Metafield
from core.database.postgres.permission import AccessRule, AccessRulesetToRule
from core import UserGroup
import core.nodecache as _nodecache
from core.permission import get_or_add_access_rule

q = db.query

logg = logging.getLogger(__name__)


def register():
    #tree.registerNodeClass("workflowstep-start", WorkflowStep_Start)
    registerStep("workflowstep_start")
    _core_translation.addLabels(WorkflowStep_Start.getLabels())


class WorkflowStep_Start(WorkflowStep):

    def show_workflow_step(self, req):
        typenames = self.get("newnodetype").split(";")
        wfnode = self.parents[0]
        redirect = ""
        message = ""

        # check existence of metadata types listed in the definition of the start node
        mdts = _nodecache.get_metadatatypes_node()
        for schema in typenames:
            if not mdts.children.filter_by(name=schema.strip().split("/")[-1]).scalar():
                return ('<i>{}: {} </i>').format(
                        schema,
                        _core_translation.t(_core_translation.set_language(req.accept_languages), "permission_denied"),
                    )

        if "workflow_start" in req.params:
            _core_translation.set_language(req.accept_languages, req.values.get('workflow_language'))
            content_class = Node.get_class_for_typestring(req.params.get('selected_schema').split('/')[0])
            node = content_class(name=u'', schema=req.params.get('selected_schema').split('/')[1])
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

        types = []
        for a in typenames:
            if a:
                m = getMetaType(a)
                # we could now check m.isActive(), but for now let's
                # just take all specified metatypes, so that edit area
                # and workflow are independent on this
                types += [(m, a)]
        cookie_error = _core_translation.t(
                _core_translation.set_language(req.accept_languages),
                "Your browser doesn't support cookies",
            )

        js = """
        <script language="javascript">
        function cookie_test() {
            if (document.cookie=="")
                document.cookie = "CookieTest=Erfolgreich";
            if (document.cookie=="") {
                alert("%s");
            }
        }
        cookie_test();
        </script>""" % cookie_error

        return _tal.processTAL(
                dict(
                    types=types,
                    id=self.id,
                    js=js,
                    starttext=self.get('starttext'),
                    languages=self.parents[0].getLanguages(),
                    currentlang=_core_translation.set_language(req.accept_languages),
                    redirect=redirect,
                    message=message,
                    allowcontinue=self.get('allowcontinue'),
                    csrf=_core_csrfform.get_token(),
                ),
                file="workflow/start.html",
                macro="workflow_start",
                request=req,
            )

    def metaFields(self, lang=None):
        ret = []
        field = Metafield("newnodetype")
        field.set("label", _core_translation.t(lang, "admin_wfstep_node_types_to_create"))
        field.set("type", "text")
        ret.append(field)
        field = Metafield("starttext")
        field.set("label", _core_translation.t(lang, "admin_wfstep_starttext"))
        field.set("type", "htmlmemo")
        ret.append(field)
        field = Metafield("allowcontinue")
        field.set("label", _core_translation.t(lang, "admin_wfstep_allowcontinue"))
        field.set("type", "check")
        ret.append(field)
        return ret

    @staticmethod
    def getLabels():
        return {"de":
                [
                    ("workflowstep-start", "Startknoten"),
                    ("admin_wfstep_starttext", "Text vor Auswahl"),
                    ("admin_wfstep_node_types_to_create", "Erstellbare Node-Typen (;-separiert)"),
                    ("admin_wfstep_allowcontinue", "Fortsetzen erlauben"),
                    ("workflow_start_create", "Erstellen"),
                    ("workflow_start_create_m", "Erstellen / Create"),
                    ("workflow_start_chooselang", u"Bitte Sprache für die Eingabe wählen / Please choose input language"),
                    ("workflow_start_type", "Melden Ihrer"),
                    ("workflow_start_type_m", "Melden Ihrer / Registering your"),
                    ("workflow_start_continue_header", "Publizieren fortsetzen"),
                    ("workflow_start_continue_header_m", "Publizieren fortsetzen / Continue publishing"),
                    ("workflow_start_identificator", "Identifikationsnummer"),
                    ("workflow_start_identificator_m", "Identifikationsnummer / Identification Number"),
                    ("workflow_start_key", u"Schlüssel"),
                    ("workflow_start_key_m", u"Schlüssel / Key"),
                    ("workflow_start_continue", "Fortsetzen"),
                    ("workflow_start_continue_m", "Fortsetzen / Continue"),
                    ("workflow_start_err_wrongkey", u"Identifikationsnummer oder Schlüssel ist nicht korrekt."),
                    ("workflow_start_err_protected", "Keine Bearbeitung erforderlich."),
                ],
                "en":
                [
                    ("workflowstep-start", "Start node"),
                    ("admin_wfstep_starttext", "Text in front of selection"),
                    ("admin_wfstep_node_types_to_create", "Node types to create (;-separated schema list)"),
                    ("admin_wfstep_allowcontinue", "Allow continue"),
                    ("workflow_start_create", "Create"),
                    ("workflow_start_create_m", "Create / Erstellen"),
                    ("workflow_start_chooselang", u"Please choose input language / Bitte Sprache für die Eingabe wählen"),
                    ("workflow_start_type", "Registering your"),
                    ("workflow_start_type_m", "Registering your / Melden ihrer"),
                    ("workflow_start_continue_header", "Publizieren fortsetzen"),
                    ("workflow_start_continue_header_m", "Continue publishing / Publizieren fortsetzen "),
                    ("workflow_start_identificator", "Identification Number"),
                    ("workflow_start_identificator_m", "Identification Number / Identifikationsnummer"),
                    ("workflow_start_key", "Key"),
                    ("workflow_start_key_m", u"Key / Schlüssel"),
                    ("workflow_start_continue", "Continue"),
                    ("workflow_start_continue_m", "Continue / Fortsetzen"),
                    ("workflow_start_err_wrongkey", 'In order to proceed, please fill out fields "Identification Number" and "Key" properly'),
                    ("workflow_start_err_protected", "no changes needed."),
                ]
                }
