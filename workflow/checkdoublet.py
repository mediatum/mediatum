"""
 mediatum - a multimedia content repository

 Copyright (C) 2007 Arne Seifert <seiferta@in.tum.de>
 Copyright (C) 2007 Matthias Kramm <kramm@in.tum.de>
 Copyright (C) 2012 Werner Neudenberger <neudenberger@ub.tum.de>

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

import time
import logging
from core import Node
from core import db
from core.systemtypes import Metadatatypes
from schema.schema import Metafield

q = db.query

try:
    import Levenshtein
except:
    pass
from .workflow import WorkflowStep, getNodeWorkflow, getNodeWorkflowStep, registerStep
from core.translation import t, lang
from schema.schema import getMetaType, getFieldsForMeta, VIEW_HIDE_EMPTY

RATIO_THRESHOLD = 0.85
DEBUG = 0


logg = logging.getLogger(__name__)


def register():
    #tree.registerNodeClass("workflowstep-checkdoublet", WorkflowStep_CheckDoublet)
    registerStep("workflowstep_checkdoublet")


def getNodeAttributeName(field):
    metafields = [x for x in field.getChildren() if x.type == 'metafield']
    if len(metafields) != 1:
        logg.error("checkdoublet: maskfield %s zero or multiple metafield child(s)", field.id)
    return metafields[0].name


def getAttributeNamesForMask(node, language, maskname="shortview"):
    res = []
    if maskname in ["shortview", "nodesmall"]:
        mask = node.getMask("nodesmall")
        for m in node.getMasks("shortview", language=language):
            mask = m
    else:
        mask = node.getMask(maskname)

    if mask:
        ordered_fields = sorted([(f.orderpos, f) for f in mask.getMaskFields()])
        for orderpos, field in ordered_fields:
            res.append(getNodeAttributeName(field))
    else:
        logg.error("checkdoublet: no mask of name %s for node %s, %s", maskname, node.id, node.type)

    return res


def getTypeForAttributename(mdt_name, attr_name):
    field = [x for x in getFieldsForMeta(mdt_name) if x.name == attr_name][0]
    return field.get('type')


def getLabelForAttributename(mdt_name, attr_name, maskname_list):
    res = attr_name

    try:
        mdt = q(Metadatatypes).one().children.filter_by(name=mdt_name).one()
        field = [x for x in getFieldsForMeta(mdt_name) if x.name == attr_name][0]

        masks = []
        for maskname in maskname_list:
            mask = mdt.children.filter_by(name=maskname).one()
            if mask.type == 'mask':
                masks.append(mask)

        set_maskitems_for_field = set([x for x in field.parents if x.type == 'maskitem'])

        for mask in masks:
            maskitems = list(set_maskitems_for_field.intersection(set(mask.children)))
            if maskitems:
                return maskitems[0].name
    except:
        pass

    return res


def getAttr(node, attributename):
    res = node.get(attributename)
    if getTypeForAttributename(node.schema, attributename).lower() == 'date':
        test = res.split('-')
        if len(test) > 2 and test[1] == '00' and len(test[0]) == 4:
            return test[0]
        res = res.replace('T', ' - ')
        if attributename.find('date') >= 0 and attributename.find('time') < 0:
            res = res.split(' - ')[0].strip()
    return res


class WorkflowStep_CheckDoublet(WorkflowStep):

    def show_workflow_node(self, node, req):
        errors = []
        steps_of_current_workflow = getNodeWorkflow(node).getSteps()
        step_children_list = [(wf_step, wf_step.getChildren()) for wf_step in steps_of_current_workflow]
        step_children_list = [(wf_step, wf_step_children, [x.id for x in wf_step_children])
                              for (wf_step, wf_step_children) in step_children_list]

        language = req.params.get('lang', 'de')

        if "gotrue" in req.params:
            chosen_id = req.params.get('chosen_id').strip()
            chosen_node = q(Node).get(chosen_id)
            if chosen_node is None:
                logg.error("checkdoublet: no such node as chosen_node: %s", chosen_id)

            all_ids = req.params.get('all_ids')
            nid_list = [x.strip() for x in all_ids.split(';')]
            nid_list = [x for x in nid_list if not x == chosen_id]

            def handleDoublets(nid_list):
                import core.xmlnode
                checked_to_remove = self.get("checked_to_remove")
                for nid in nid_list:
                    n = q(Node).get(nid)
                    if n:
                        for wf_step, wf_step_children, wf_step_children_ids in step_children_list:
                            if n.id in wf_step_children_ids:
                                if checked_to_remove:
                                    current_workflow = getNodeWorkflow(node)
                                    logg.info("checkdoublet: going to remove node %s (doublette of node %s) from workflowstep '%s' (%s) of workflow '%s' (%s)",
                                              nid, chosen_id, wf_step.name, wf_step.id, current_workflow.name, current_workflow.id)
                                    wf_step.children.remove(n)
                                    db.session.commit()

            handleDoublets(nid_list)

            wf_step_of_chosen_node = getNodeWorkflowStep(chosen_node)
            req.params['key'] = chosen_node.get('key')

            try:
                del req.params['gotrue']
            except:
                pass
            try:
                del req.params['gofalse']
            except:
                pass

            return wf_step_of_chosen_node.show_workflow_node(chosen_node, req)

        if "gofalse" in req.params:
            return self.forwardAndShow(node, False, req)

        schema = node.schema
        attribute_names_string = self.get("attribute_names").strip()
        attribute_names = []
        if attribute_names_string:
            attribute_names = [x.strip() for x in attribute_names_string.split(';') if x.strip()]

        exact_field = self.get("exact_field").strip()

        all_attribute_names = [field.name for field in getFieldsForMeta(schema)]

        additional_attributes = []
        additional_attributes_string = self.get("additional_attribute_to_show").strip()
        if additional_attributes_string.strip().lower() == "mask:all":
            additional_attributes = all_attribute_names
        elif additional_attributes_string.startswith('mask:'):
            maskname = additional_attributes_string[len('mask:'):]
            try:
                additional_attributes = getAttributeNamesForMask(node, language, maskname)
            except:
                msg = "checkdoublet: no mask found for %s (from %s)" % (maskname, additional_attributes_string)
                errors.append(msg)
        else:
            additional_attributes = [x.strip() for x in additional_attributes_string.split(';') if x.strip()]

        additional_attributes = [x for x in additional_attributes if x not in attribute_names]

        masklist_for_labels = self.get("masklist_for_labels").strip().split(';')
        masklist_for_labels = [x.strip() for x in masklist_for_labels if x.strip()]

        dict_labels = dict([(attr_name, getLabelForAttributename(schema, attr_name, masklist_for_labels))
                            for attr_name in attribute_names + additional_attributes])

        additional_attributes_decorated = sorted([(dict_labels[x], x) for x in additional_attributes])
        additional_attributes = [x[1] for x in additional_attributes_decorated if not x[1] in attribute_names]

        if exact_field not in all_attribute_names:
            msg_tuple = (getNodeWorkflow(node).id, self.id, exact_field, schema, node.id)
            msg = "checkdoublet: workflow %s, step %s (doubletcheck): exact_field '%s' not in schema '%s' of current node %s: contact administrator" % msg_tuple
            errors.append(msg)
            logg.error(msg)

        if set(attribute_names) - set(all_attribute_names):
            msg_tuple = (getNodeWorkflow(node).id, self.id, unicode(set(attribute_names) - set(all_attribute_names)), schema, node.id)
            msg = "checkdoublet: workflow %s, step %s (doubletcheck): attribute_names '%s' not in schema '%s' of current node %s: contact administrator" % msg_tuple
            errors.append(msg)
            logg.error(msg)

        doublets = []

        if exact_field:
            exact_value = node.get(exact_field)

        if attribute_names:
            attribute_values_string = ("#".join([node.get(attr) for attr in attribute_names])).lower()

        for wf_step, wf_step_children, wf_step_children_ids in step_children_list:
            for candidate in wf_step_children:
                if exact_field:
                    if exact_value != candidate.get(exact_field):
                        continue
                if attribute_names:
                    candidate_values_string = ("#".join([candidate.get(attr) for attr in attribute_names])).lower()
                    try:
                        ratio = Levenshtein.ratio(attribute_values_string, candidate_values_string)
                    except:
                        ratio = int(attribute_values_string == candidate_values_string)

                    if ratio >= RATIO_THRESHOLD:
                        doublets.append([candidate.get('creationtime').replace('T', ' - '), wf_step, candidate, ratio])
                else:
                    if exact_field:
                        # when no attribute_names are given, the exacte_filed alone shall decide
                        doublets.append([candidate.get('creationtime').replace('T', ' - '), wf_step, candidate, 1.0])

        sorted_doublets = sorted(doublets)
        doublets = []
        for i, t in enumerate(sorted_doublets):
            doublets.append(t + [i])

        context = {"key": req.params.get("key", req.session.get("key", "")),
                   "error": "\n".join(errors),
                   "node": node,
                   "show_attributes": attribute_names + additional_attributes,
                   "doublets": doublets,
                   "ids": ";".join([x[2].id for x in doublets]),
                   "prefix": self.get("prefix"),
                   "suffix": self.get("suffix"),
                   "dict_labels": dict_labels,
                   "getAttr": getAttr,
                   "buttons": self.tableRowButtons(node)}

        if len(doublets) == 1:
            logg.debug('checkdoublet: node %s: no doublet found', node.id)
            return self.forwardAndShow(node, True, req)

        atime = time.time()
        res = req.getTAL("workflow/checkdoublet.html", context, macro="workflow_checkdoublet")
        etime = time.time()
        logg.debug('checkdoublet: duration getTAL: %.3f', etime - atime)

        return res

    def metaFields(self, lang=None):
        ret = list()
        field = Metafield("prefix")
        field.set("label", t(lang, "admin_wfstep_text_before_data"))
        field.set("type", "memo")
        ret.append(field)

        field = Metafield("suffix")
        field.set("label", t(lang, "admin_wfstep_text_after_data"))
        field.set("type", "memo")
        ret.append(field)

        field = Metafield("attribute_names")
        field.set("label", t(lang, "admin_wfstep_checkdoublet_names_of_attributes_to_check"))
        field.set("type", "text")
        ret.append(field)

        field = Metafield("exact_field")
        field.set("label", t(lang, "admin_wfstep_checkdoublet_exact_field"))
        field.set("type", "text")
        ret.append(field)

        field = Metafield("additional_attribute_to_show")
        field.set("label", t(lang, "admin_wfstep_checkdoublet_additional_attribute_to_show"))
        field.set("type", "text")
        ret.append(field)

        field = Metafield("masklist_for_labels")
        field.set("label", t(lang, "admin_wfstep_checkdoublet_masklist_for_labels"))
        field.set("type", "text")
        ret.append(field)

        field = Metafield("checked_to_remove")
        field.set("label", t(lang, "admin_wfstep_checkdoublet_check_to_remove"))
        field.set("type", "check")
        ret.append(field)
        return ret
