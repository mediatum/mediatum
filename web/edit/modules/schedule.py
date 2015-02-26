"""
 mediatum - a multimedia content repository

 Copyright (C) 2010 Werner Neudenberger <neudenberger@ub.tum.de>
 Copyright (C) 2010 Matthias Kramm Neudenberger <kramm@in.tum.de>
 Copyright (C) 2010 Arne Seifert <seiferta@in.tum.de>

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

import sys
import logging
import re
import inspect

from datetime import datetime, time

import core.users as users

import core.acl as acl
import utils.scheduleutils as su

from core.translation import lang, t, getDefaultLanguage
from utils.pathutils import isDescendantOf
from utils.utils import dec_entry_log
from core.transition import httpstatus

if sys.version[0:3] < '2.6':
    import simplejson as json
else:
    import json


logg = logging.getLogger(__name__)


ALLOWED_CHARACTERS = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ' + \
    '0123456789' + '+-_.'


def normalizeString(s, chars=ALLOWED_CHARACTERS):
    res = ''
    for c in s:
        if c in chars:
            res += c
        else:
            res += '_'
    return res


@dec_entry_log
def getContent(req, ids):

    reload(su)

    language = lang(req)
    user = users.getUserFromRequest(req)
    username = user.getName()
    #access = acl.AccessData(user=user)
    access = acl.AccessData(req=req)

    if "schedule" in users.getHideMenusForUser(user):
        req.setStatus(httpstatus.HTTP_FORBIDDEN)
        return req.getTAL("web/edit/edit.html", {}, macro="access_error")

    errors = []
    error = ''

    if "action" in req.params.keys():
        action = req.params.get("action")
        if action.startswith("get_fields_for_"):
            schedule_func = req.params.get(
                "action").replace("get_fields_for_", "")
            fields = su.fc_dict[schedule_func].getMetafields(lang(req))
            fieldDicts = su.fc_dict[schedule_func].getMetafieldDicts(lang(req))

            field_errors = []
            for i, field in enumerate(fields):
                field_errors.append(False)

            d = {
                'fields': fields,
                'fieldDicts': fieldDicts,
                'currentField': fields[0],
                'field_errors': field_errors,
                'currentFunction': schedule_func,
                'explain_func': su.fc_dict[schedule_func].getExplanation(language)
            }

            req.writeTAL("web/edit/modules/schedule.html", d,
                         macro="schedule_func_show_fields_and_explanation")
            return ""

        elif action.startswith("load_schedule_"):
            schedule_id = action.replace("load_schedule_", "")
            try:
                schedule = tree.getNode(schedule_id)
            except:
                errors.append("edit_schedule_no_such_node_error")
                return "no such schedule error"

            if not schedule.type == "schedule" and access and access.hasWriteAccess(schedule):
                return "schedule access error"

            schedule_func = schedule.get("function")
            if schedule_func:
                fields = su.fc_dict[schedule_func].getMetafields(lang(req))
                fieldDicts = su.fc_dict[
                    schedule_func].getMetafieldDicts(lang(req))
                d['explain_func'] = su.fc_dict[
                    schedule_func].getExplanation(language)
            else:
                fields = []
                fieldDicts = []
                d['explain_func'] = ""

            field_errors = []
            for i, field in enumerate(fields):
                field_errors.append(False)

            has_evaluation_errors = False
            for i, dfield in enumerate(fieldDicts):
                field_name = dfield['field_name']
                field_value = schedule.get(field_name)
                dfield['value'] = field_value
                field_validator_func = dfield['field_validator_func']
                if field_validator_func and not field_validator_func(field_value):
                    dfield['evaluation_error'] = True
                    has_evaluation_errors = True
                else:
                    dfield['evaluation_error'] = False

            if has_evaluation_errors:
                error = "\n<br/>\n".join([error, t(language,
                                                   'edit_schedule_field_validation_error')])

            d = {
                'fields': fields,
                'fieldDicts': fieldDicts,
                'currentField': fields[0],
                'field_errors': field_errors,
                'currentFunction': schedule_func,
            }

            req.writeTAL("web/edit/modules/schedule.html", d,
                         macro="schedule_func_show_fields_and_explanation")
            return ""

        elif action == "delete_node_from_schedule":

            node_id = req.params.get('node_id', None)

            if node_id:
                pass
            else:
                errors.append("edit_schedule_unexpected_no_such_node")

            schedule_id = req.params.get('schedule_id', None)
            if schedule_id:
                try:
                    schedule = tree.getNode(schedule_id)
                except:
                    errors.append(
                        "edit_schedule_unexpected_no_such_schedule_node")
            else:
                errors.append("edit_schedule_unexpected_no_such_schedule_node")

            delete_errors = su.deleteNodeIDsFromSchedule(
                [node_id], schedule_id, access=access)

            if not delete_errors:
                logg.info("user '%s' removed node %s from schedule '%s' (%s)", username, node_id, schedule.name, schedule_id)
            else:
                error_msg = ", ".join([t(language, e) for e in delete_errors])
                logg.error("user '%s' tried to remove node %s from schedule '%s' (%s): %s" , 
                           username, node_id, schedule.name, schedule_id, error_msg)

            errors += delete_errors

            s = {}
            s['errors'] = errors
            s['delete_errors'] = delete_errors

            s['delete_table_rows'] = ['sid_%s' % schedule_id]

            res_msg = req.params.get(
                "jsoncallback") + "(%s)" % json.dumps(s, indent=4)
            req.write(res_msg)
            return ""

        elif action == "delete_schedule":
            schedule_id = req.params.get('schedule_id', None)
            if schedule_id:
                try:
                    schedule = tree.getNode(schedule_id)
                except:
                    errors.append(
                        "edit_schedule_unexpected_no_such_schedule_node")
            else:
                errors.append("edit_schedule_unexpected_no_such_schedule_node")

            delete_errors = su.deleteSchedule(schedule_id, access=access)

            if not delete_errors:
                logg.info("user '%s' removed schedule %s (%s)", username, schedule.name, schedule_id)
            else:
                error_msg = ", ".join([t(language, e) for e in delete_errors])
                logg.error("user '%s' tried to remove schedule '%s' (%s): %s", username, schedule.name, schedule_id, error_msg)

            errors += delete_errors

            s = {}
            s['errors'] = errors
            s['delete_errors'] = delete_errors
            s['delete_table_rows'] = ['sid_%s' % schedule_id]

            res_msg = req.params.get(
                "jsoncallback") + "(%s)" % json.dumps(s, indent=4)
            req.write(res_msg)
            return ""

        elif action == "load_table_nid2schedules":

            nid2schedules, schedule2nids, nid2active_schedules = su.getSchedulesForIds(
                ids, access=access, language=language)

            nid2schedules_attrs = {}
            for nid in nid2schedules:
                nid2schedules_attrs[nid] = [
                    [s.id, s.name, s.get("single_trigger")] for s in nid2schedules[nid]['schedule_list']]

            d = {}
            d['nid2schedules'] = nid2schedules
            d['nid2active_schedules'] = nid2active_schedules
            d['errors'] = ['testerror1', 'testerror1']
            d['date'] = datetime.now().isoformat()
            d['isActive'] = su.isActive

            req.writeTAL(
                "web/edit/modules/schedule.html", d, macro="table_nid2schedules")
            return ""

        elif action == "load_table_schedule2nids":

            nid2schedules, schedule2nids, nid2active_schedules = su.getSchedulesForIds(
                ids, access=access, language=language)

            nid2schedules_attrs = {}
            for nid in nid2schedules:
                nid2schedules_attrs[nid] = [
                    [s.id, s.name, s.get("single_trigger")] for s in nid2schedules[nid]['schedule_list']]

            d = {}
            d['nid2schedules'] = nid2schedules
            d['schedule2nids'] = schedule2nids
            d['nid2active_schedules'] = nid2active_schedules
            d['errors'] = ['testerror1', 'testerror1']
            d['date'] = datetime.now().isoformat()
            d['isActive'] = su.isActive

            req.writeTAL(
                "web/edit/modules/schedule.html", d, macro="table_schedule2nids")
            return ""

    nid2schedules, schedule2nids, nid2active_schedules = su.getSchedulesForIds(
        ids, access=access, language=language)

    datetime_str = req.params.get("datetime", "").strip()
    datetime_error = False
    has_evaluation_errors = False

    if datetime_str:
        patter = "^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$"
        if not re.match(patter, datetime_str):
            error = t(
                language, "edit_schedule_input_datetime_format_error") % datetime_str
            datetime_error = True
        else:
            try:
                parser_test_result = datetime.strptime(
                    datetime_str, "%Y-%m-%dT%H:%M")  # "%Y-%m-%dT%H:%M:%S.%f"
            except:
                parser_test_result = None
                error = t(
                    language, "edit_schedule_input_datetime_format_error") % datetime_str
                datetime_error = True
            if parser_test_result and datetime_str <= datetime.now().isoformat():
                error = t(
                    language, "edit_schedule_input_datetime_already_past_error") % datetime_str
                datetime_error = True
    elif "submit" in req.params:
        error = t(
            language, "edit_schedule_input_datetime_format_error") % datetime_str
        datetime_error = True

    schedule_id = req.params.get("schedule_id", "")
    if schedule_id:
        schedule = tree.getNode(schedule_id)
        if access and not access.hasWriteAccess(schedule):
            errors.append("edit_schedule_no_access_error")
            schedule = None
            current_function = req.params.get('schedule_function', '')
        else:
            current_function = schedule.get("function")
    else:
        schedule = None
        current_function = req.params.get('schedule_function', '')

    if "submit" in req.params or "submit_run_now" in req.params:
        current_function = req.params.get('schedule_function', '')
        if current_function in su.fc_dict:
            field_descriptors = su.fc_dict[
                current_function].getFieldDescriptors()
            field_errors = []
        else:
            # should not happen
            logg.error("-> unexpected error: 'non-existant schedule function' requested in module %s: :s", 
                       __file__, inspect.currentframe().f_lineno)

    d = {
        "id": req.params.get("id")
    }

    # nodes list is used to display icons in upper part of page
    # additional nodes should not / will not be shown there
    nodes = []
    for nid in ids:
        node = tree.getNode(nid)
        nodes.append(node)

    d['nodes'] = nodes

    if current_function in su.fc_dict:
        fields = su.fc_dict[current_function].getMetafields(lang(req))
        fieldDicts = su.fc_dict[current_function].getMetafieldDicts(lang(req))
        d['explain_func'] = su.fc_dict[
            current_function].getExplanation(language)
    else:
        fields = []
        fieldDicts = []
        d['explain_func'] = ""

    if not "submit_run_now" in req.params:
        has_evaluation_errors = datetime_error

    if schedule and not "submit" in req.params and not "submit_run_now" in req.params:
        for i, dfield in enumerate(fieldDicts):
            field_name = dfield['field_name']
            field_value = schedule.get(field_name)
            dfield['value'] = field_value
            field_validator_func = dfield['field_validator_func']
            if field_validator_func and not field_validator_func(field_value):
                dfield['evaluation_error'] = True
                has_evaluation_errors = True
            else:
                dfield['evaluation_error'] = False
    else:
        for i, dfield in enumerate(fieldDicts):
            field_name = dfield['field_name']
            # m_* classes from metadata/ are not multilingual for schedules
            # their getEditorHTML methods are used to display schedule node
            # attributes
            field_value = req.params.get(
                getDefaultLanguage() + '__' + field_name, '')
            dfield['value'] = field_value
            field_validator_func = dfield['field_validator_func']
            if field_validator_func and not field_validator_func(field_value):
                dfield['evaluation_error'] = True
                has_evaluation_errors = True
            else:
                dfield['evaluation_error'] = False

    additional_nodes_str = req.params.get("additional_nodes", "")
    additional_nodes_error = False
    additional_nodes_bad_ids = []

    try:
        additional_nodes_id_list = [
            ustr(int(nid.strip())) for nid in additional_nodes_str.strip().split(";") if nid.strip()]
    except:
        has_evaluation_errors = True
        additional_nodes_error = True
        additional_nodes_id_list = []
        errors.append(
            "edit_schedule_additional_nodes_list_not_semikolon_separated_list_of_integers")

    if not additional_nodes_error:
        collections_root = tree.getRoot("collections")
        for nid in additional_nodes_id_list:
            n = None
            try:
                n = tree.getNode(nid)
            except tree.NoSuchNodeError as e:
                has_evaluation_errors = True
                additional_nodes_error = True
                if nid not in additional_nodes_bad_ids:
                    additional_nodes_bad_ids.append(nid)
            if n and (not isDescendantOf(n, collections_root) or not access.hasWriteAccess(n)):
                # to do? discussion: override collections rectriction for
                # admins ?
                has_evaluation_errors = True
                additional_nodes_error = True
                if nid not in additional_nodes_bad_ids:
                    additional_nodes_bad_ids.append(nid)

    if additional_nodes_bad_ids:
        has_evaluation_errors = True
        additional_nodes_error = True
        errors.append(t(language, "edit_schedule_additional_nodes_bad_ids") +
                      (";".join(additional_nodes_bad_ids)))

    if has_evaluation_errors:
        errors.append('edit_schedule_field_validation_error')
        error = "\n<br/>\n".join(map(lambda x:
                                     t(language, x), [error] + errors))

    d['fields'] = fields
    d['fieldDicts'] = fieldDicts
    d['field_errors'] = [False] * len(fields)
    d['currentField'] = None
    d['currentFunction'] = current_function

    d['error'] = error

    d['fc_dict'] = su.filter_access(su.fc_dict, access)

    d['input_datetime'] = datetime_str
    d['input_datetime_error'] = datetime_error

    d['nid2schedules'] = nid2schedules
    d['schedule2nids'] = schedule2nids
    d['nid2active_schedules'] = nid2active_schedules

    d['loaded_schedule'] = schedule

    if schedule:
        d['loaded_schedule_id'] = ustr(schedule.id)
    else:
        d['loaded_schedule_id'] = None

    d['mklink'] = su.mklink

    d['language'] = language
    d['t'] = t
    d['isActive'] = su.isActive

    d['result'] = ''

    d['created_new_schedule'] = False

    d['additional_nodes'] = additional_nodes_str
    d['additional_nodes_error'] = additional_nodes_error

    d['submitbutton_run_now_label'] = t(
        language, 'edit_schedule_submit_run_now_button')
    d['edit_schedule_submit_run_now_button_confirm'] = t(
        language, 'edit_schedule_submit_run_now_button_confirm')
    d['edit_schedule_delete_schedule_confirm'] = t(
        language, 'edit_schedule_delete_schedule_confirm')

    if has_evaluation_errors and not ('submit_run_now' in req.params):
        return req.getTAL("web/edit/modules/schedule.html", d, macro="schedule_popup")

    new_schedule = None
    if (not schedule and "submit" in req.params) or "submit_run_now" in req.params:

        new_schedule_name = user.name + \
            "_created_at_" + datetime.now().isoformat()
        new_schedule = tree.Node(new_schedule_name, 'schedule')

        username = user.getName()
        new_schedule.setAccess("write", "{user %s}" % username)

        if not "submit_run_now" in req.params:
            schedules = tree.getRoot("schedules")
            schedules.addChild(new_schedule)

            msg = "user '%s' created new schedule '%s' (%s), trigger='%s', function='%s', nodelist='%s'" % (
                username, new_schedule.name, str(new_schedule.id), datetime_str, d['currentFunction'], new_schedule.get('nodelist'))
            logg.info(msg)

            d['result'] = t(
                language, 'edit_schedule_result_new_schedule_created')
            d['created_new_schedule'] = True
        else:
            msg = "user '%s' created temporary schedule '%s' (%s), trigger='%s', function='%s', nodelist='%s'" % (
                username, new_schedule.name, str(new_schedule.id), datetime_str, d['currentFunction'], new_schedule.get('nodelist'))
            logg.info(msg)

            d['result'] = t(
                language, 'edit_schedule_result_temporary_schedule_created')
            d['created_temporary_schedule'] = True

    elif (schedule) and ("submit" in req.params):
        new_schedule = schedule
        msg = "user '%s' is editing schedule '%s' (%s), trigger='%s', function='%s', nodelist='%s'" % (
            username, new_schedule.name, str(new_schedule.id), datetime_str, d['currentFunction'], new_schedule.get('nodelist'))
        logg.info(msg)
        new_schedule.set("system.edited", datetime.now().isoformat())

        d['result'] = t(
            language, 'edit_schedule_result_existing_schedule_edited')

    if new_schedule:
        for i, dfield in enumerate(fieldDicts):
            field_name = dfield['field_name']
            field_value = dfield['value']
            new_schedule.set(field_name, field_value)

        ids_plus_additional_nodes = ids
        for nid in additional_nodes_id_list:
            if nid not in ids_plus_additional_nodes:
                ids_plus_additional_nodes.append(nid)

        new_schedule.set('function', d['currentFunction'])
        new_schedule.set('nodelist', ",".join(ids_plus_additional_nodes))
        new_schedule.set('single_trigger', datetime_str)

        if datetime.now().isoformat() < datetime_str:
            new_schedule.set('single_trigger_status', '')

        if "submit_run_now" in req.params:
            new_schedule.set("single_trigger", datetime.now().isoformat())
            has_fired, has_error, TT = su.handle_single_trigger(
                new_schedule, datetime.now().isoformat(), su.OUT)
            if has_error:
                _error1 = d['error']
                _error2 = "<br/>\n".join(map(lambda x:
                                             (t(language, ustr(x))), TT))
                _error = "<br/>\n".join([_error1, _error2])
                d['error'] = _error

    return req.getTAL("web/edit/modules/schedule.html", d, macro="schedule_popup")
