"""
 mediatum - a multimedia content repository

 Copyright (C) 2007 Arne Seifert <seiferta@in.tum.de>
 Copyright (C) 2007 Matthias Kramm <kramm@in.tum.de>
 Copyright (C) 2012 Werner F. Neudenberger <neudenberger@ub.tum.de>

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

from datetime import datetime, timedelta
import json
import sys
import os
import time
import traceback
import logging
import random

import threading

import core.tree as tree
import core.config as config
import core.acl as acl
import core.schedules

from core.translation import t

from metadata.check import m_check
from metadata.htmlmemo import m_htmlmemo
from metadata.memo import m_memo
from metadata.text import m_text
from metadata.treeselect import m_treeselect


logger = logging.getLogger("backend")

SLEEP_INTERVAL = 1
TRIGGER_INTERVAL = 3600  # seconds (times SLEEP_INTERVAL)
DEBUG = False

GRACE_SECONDS = 60
MAX_CRON_HISTORY = 20

RUN_METHODS = ["function", "thread", "process"]
DEFAULT_RUN_METHOD = RUN_METHODS[1]


# dictionary for functions
f_dict = {}

# dictionary for classes
fc_dict = {}

dict_type2class = {
    'check': m_check,
    'htmlmemo': m_htmlmemo,
    'memo': m_memo,
    'text': m_text,
    'treeselect': m_treeselect,
}


class LogWriter:

    def __init__(self, logger, level=logging.INFO):
        self.logger = logger
        self.level = level

    def write(self, s):
        for line in str(s).splitlines():
            self.logger.log(self.level, line)


def OUT(msg, logger='backend', print_stdout=False, level='info'):
    if logger:
        getattr(logging.getLogger(logger), level)(msg)
    if print_stdout:
        print msg
        sys.stdout.flush()


def register_schedule_func(name, func, force=False):
    if name in f_dict and not force:
        raise ValueError("function name '%s' exists already" % name)
        return
    f_dict[name] = func


def update_schedule_func(name, func, force=False):
    if name not in f_dict and not force:
        raise ValueError("function name '%s' does not exist" % name)
        return
    f_dict[name] = func


def match_date_dict(dt, d, granularity=['hours', 'minutes', 'seconds'][1]):
    res = True
    if 'weekday' in d and d['weekday'] and not dt.__getattribute__('weekday')() in d['weekday']:
        res = False
    for k in ['month', 'day', 'hour', 'minute', 'second']:
        if k in d and d[k] and not dt.__getattribute__(k) in d[k]:
            res = False
        if k == granularity:
            break
    return res


def iter_date(start_datetime_obj, d, granularity=['hours', 'minutes', 'seconds'][1], lookahead=24 * 60, lookback=60):

    delta = timedelta(**{granularity: 1})

    if granularity == 'hours':
        start = datetime(*tuple(start_datetime_obj.timetuple())[0:4])
    elif granularity == 'seconds':
        start = datetime(*tuple(start_datetime_obj.timetuple())[0:6])
    else:
        start = datetime(*tuple(start_datetime_obj.timetuple())[0:5])

    dts = [start + i * delta for i in range(-lookback, lookahead)]

    for dt in dts:
        if match_date_dict(dt, d):
            yield dt


def isIsoformat(str):
    try:
        datetime.strptime(datetime_str, "%Y-%m-%dT%H:%M:%S")
        return True
    except:
        return False


def assert_is_cron_dict(d):
    assert isinstance(d, dict), "not a dict"
    for k in d:
        assert k in ['month', 'day', 'weekday', 'hour', 'minute', 'second'], "key '%s' not admissible" % k
        v = d[k]
        assert isinstance(v, list), "value for key '%s' is not a list" % k
        assert len(v) <= 61, "value list for key '%s' too long" % k
        for i in v:
            assert isinstance(i, int), "value list for key '%s' contains non-integer '%s'" % (k, str(i))


class WrappedThread(threading.Thread):

    def run(self):
        try:
            threading.Thread.run(self)
        except:
            thread_name = str(threading.currentThread().name)


def traced(func_class_instance):
    def wrapper(*__args, **__kw):
        error = None
        thread_name = __kw['thread_name']
        if thread_name not in core.schedules.action_dict.keys():
            core.schedules.action_dict[thread_name] = {}
        try:
            return func_class_instance.function(*__args, **__kw)
        except Exception as e:
            error = e
            core.schedules.action_dict[thread_name]["status"] = "error"
            core.schedules.action_dict[thread_name]["error"] = "%s" % (datetime.now().isoformat())
            core.schedules.action_dict[thread_name]["error_type"] = "%s" % (str(e))

            s = traceback.format_exc()

            core.schedules.action_dict[thread_name]["error_traceback"] = "%s" % (s)
        finally:
            if not error:
                etime = time.time()
                core.schedules.action_dict[thread_name]["status"] = "ended"
                core.schedules.action_dict[thread_name]["ended"] = "%s" % (datetime.now().isoformat())
                core.schedules.action_dict[thread_name]["end_timestamp"] = etime
                atime = core.schedules.action_dict[thread_name]["start_timestamp"]
                core.schedules.action_dict[thread_name]["duration_seconds"] = "%.3f" % (etime - atime)
    return wrapper


def run_as_function(func_class_instance, s, trigger, now_str, trigger_info, OUT, TT):

    atime = time.time()

    has_fired = False
    has_error = False

    try:
        func = traced(func_class_instance)
        thread_name = "function_single_%s_%s" % (trigger, now_str)

        dthreads = core.schedules.action_dict
        dthreads[thread_name] = {
            "type": "single_trigger",
            "trigger_info": trigger_info,
            "trigger": trigger,
            "started": now_str,
            "status": "started",
            "name": thread_name,
            "start_timestamp": time.time(),
            "start_datetime": datetime.now().isoformat(),
            "thread_obj": None,
        }

        core.schedules.action_dict = dthreads.copy()

        res = func_class_instance.function(s, trigger=trigger, now_str=now_str, trigger_info=trigger_info, OUT=OUT, TT=TT)

        has_fired = True
        msg = "%s %s: executed function '%s', node '%s' (%s)" % (
            trigger_info, trigger, func_class_instance.longname, str(s.name), str(s.id))
        s.set("single_trigger_status", "OK: %s: %s" % (now_str, msg))
        TT.append([msg, time.time() - atime])
        atime = time.time()
    except:

        has_error = True
        msg = "Error while executing function '%s': %s %s" % (func_class_instance.longname, str(sys.exc_info()[0]), str(sys.exc_info()[1]))
        s.set("single_trigger_status", "FAIL: %s: %s" % (now_str, msg))
        TT.append([msg, time.time() - atime])
        atime = time.time()
        OUT(msg, logger='backend', print_stdout=True, level='error')

    return has_fired, has_error, TT


def run_as_thread(func_class_instance, s, trigger, now_str, trigger_info, OUT, TT):
    atime = time.time()

    has_fired = False
    has_error = False

    try:
        func = traced(func_class_instance)
        thread_name = "thread_single_%s_%s" % (trigger, now_str)
        wt = WrappedThread(
            name=thread_name,
            target=func,
            args=(
                s,
            ),
            kwargs={
                "trigger": trigger,
                "now_str": now_str,
                "trigger_info": trigger_info,
                "OUT": OUT,
                "TT": TT,
                "thread_name": thread_name,
                "func": func,
            })
        wt.start()
        dthreads = core.schedules.action_dict
        dthreads[thread_name] = {
            "type": "single_trigger",
            "trigger_info": trigger_info,
            "trigger": trigger,
            "started": now_str,
            "status": "started",
            "name": thread_name,
            "start_timestamp": time.time(),
            "start_datetime": datetime.now().isoformat(),
            "thread_obj": wt,
        }
        core.schedules.action_dict = dthreads.copy()

        has_fired = True
        msg = "%s %s: executed function '%s', node '%s' (%s)" % (
            trigger_info, trigger, func_class_instance.longname, str(s.name), str(s.id))
        s.set("single_trigger_status", "OK: %s: %s" % (now_str, msg))
        TT.append([msg, time.time() - atime])
        atime = time.time()
    except:
        has_error = True
        msg = "Error while executing function '%s': %s %s" % (func_class_instance.longname, str(sys.exc_info()[0]), str(sys.exc_info()[1]))
        s.set("single_trigger_status", "FAIL: %s: %s" % (now_str, msg))
        TT.append([msg, time.time() - atime])
        atime = time.time()
        OUT(msg, logger='backend', print_stdout=True, level='error')
    return has_fired, has_error, TT


def run_as_process(func, s, trigger, now_str, trigger_info, OUT, TT):

    has_fired = False
    has_error = False
    TT = []

    sid = s.id

    if not sid:

        from .utils import join_paths
        import pickle

        n_dict = {
            'node_id': '',
            'node_name': s.name,
            'node_type': s.type,
            'items': s.items(),
            'file': [(f.getName(), f.getType(), f.getMimeType(), f.retrieveFile()) for f in s.getFiles()]
        }

        tempfile = join_paths(config.get("paths.tempdir"), 'temp_schedule_' + trigger.replace(":", "_") + '_RND_' + str(random.random()))
        f = open(tempfile, "w")
        pickle.dump(n_dict, f)
        f.close()
        script_to_detach_with_args = 'bin/run_single_schedule.py ' + str(s.id)
    else:
        script_to_detach_with_args = 'bin/run_single_schedule.py ' + str(s.id) + ' ' + trigger

    os.system('python utils/run_script_as_process.py %s ' % script_to_detach_with_args)
    s.set("single_trigger_status", "ok...")

    return has_fired, has_error, TT


def handle_single_trigger(s, now_str, OUT):

    atime = time.time()
    has_fired = False
    has_error = False
    TT = []
    datetime_str = s.get("single_trigger").strip()
    if datetime_str and datetime_str <= now_str and not s.get("single_trigger_status").strip():
        trigger = datetime_str
        trigger_info = "single_trigger"
        schedule_node = s
        func_name = s.get('function')
        if func_name in fc_dict:
            func_object = fc_dict[func_name]
            func = func_object.function
            run_as = func_object.run_as
            if s.id:
                sid = s.id
            else:
                sid = 'temporary schedule (immediate execution)'
                run_as = func_object.run_as_immediate
            msg = "scheduler going to run schedule '%s' (%s) function '%s' as '%s'" % (str(s.name), sid, str(func_name), str(run_as))
            logger.info(msg)

            if run_as not in RUN_METHODS:
                run_as = DEFAULT_RUN_METHOD

            if run_as == "function":
                trigger_info = "single_trigger-function"
                has_fired, has_error, TT = run_as_function(func_object, schedule_node, trigger, now_str, trigger_info, OUT, TT)

            elif run_as == "thread":
                trigger_info = "single_trigger-thread"
                has_fired, has_error, TT = run_as_thread(func_object, schedule_node, trigger, now_str, trigger_info, OUT, TT)

            elif run_as == "process":
                trigger_info = "single_trigger-process"
                has_fired, has_error, TT = run_as_process(func_object, schedule_node, trigger, now_str, trigger_info, OUT, TT)

            else:
                has_error = True
                msg = "Error while executing function '%s': %s %s" % (func_name, str(sys.exc_info()[0]), str(sys.exc_info()[1]))
                s.set("single_trigger_status", "FAIL: %s: %s" % (now_str, msg))
                TT.append([msg, time.time() - atime])
                atime = time.time()
                OUT(msg, logger='backend', print_stdout=True, level='error')

        else:
            has_error = True
            msg = "WARNING: function '%s' for node '%s' (%s) is not defined" % (func_name, str(s.name), str(s.id))
            s.set("single_trigger_status", "FAIL: %s: %s" % (now_str, msg))
            TT.append([msg, time.time() - atime])
            atime = time.time()

    return has_fired, has_error, TT


def handle_cron_dict(s, now_obj, OUT):
    atime = time.time()
    has_fired = False
    has_error = False
    TT = []
    s_name = s.name
    s_id = str(s.id)

    error_msg, triggers = s.get_cron_triggers(datetime.now(), lookahead=60 * 2, lookback=60, tostring=False)

    if error_msg:
        has_error = True
        TT.append([error_msg, time.time() - atime])
        atime = time.time()
        return

    grace_seconds_str = s.get('grace_seconds').strip()
    if grace_seconds_str:
        try:
            grace_seconds = int(grace_seconds_str)
            grace = timedelta(seconds=grace_seconds)
            msg = "using %d grace seconds for node '%s' (%s)" % (grace_seconds, s_name, s_id)
            TT.append([msg, time.time() - atime])
            atime = time.time()
        except:
            has_error = True
            msg = "ERROR: could not parse grace seconds '%s' for node '%s' (%s)" % (grace_seconds_str, s_name, s_id)
            TT.append([msg, time.time() - atime])
            atime = time.time()
    else:
        grace = timedelta(seconds=GRACE_SECONDS)
        msg = "using default grace seconds '%s' for node '%s' (%s)" % (str(GRACE_SECONDS), s_name, s_id)
        TT.append([msg, time.time() - atime])
        atime = time.time()

    for t in triggers:

        if t > now_obj:
            continue

        time_overdue = now_obj - t

        if time_overdue > grace:
            continue

        # this trigger should fire - if not done already
        func_name = s.get('function')
        if func_name in fc_dict:
            func_object = fc_dict[func_name]
            func = func_object.function
            run_as = func_object.run_as
            if s.id:
                sid = s.id
            else:
                sid = 'temporary schedule (immediate execution)'
                run_as = func_object.run_as_immediate
            msg = "scheduler going to run schedule '%s' (%s) function '%s' as '%s'" % (str(s.name), sid, str(func_name), str(run_as))
            logger.info(msg)

            if run_as not in RUN_METHODS:
                run_as = DEFAULT_RUN_METHOD
            try:

                history_str = s.get('cron_history').strip()
                if not history_str:
                    history_str = '[]'

                try:
                    history = json.loads(history_str)
                    assert isinstance(history, list)
                except:
                    has_error = True
                    msg = "error decoding history string to json for node '%s' (%s): %s" % (s.name, s.id, history_str)
                    TT.append([msg, time.time() - atime])
                    atime = time.time()
                    logger.error(msg)
                    break

                # history format: [['result_code', 'isodate_trigger', 'isodate_fired'], ...]
                t_str = t.isoformat()
                if t_str in [x[1] for x in history]:
                    break
                try:
                    schedule_node = s
                    trigger = t
                    now_str = datetime.now().isoformat()

                    if run_as == "function":
                        trigger_info = "cron_trigger-function"
                        has_fired, has_error, TT = run_as_function(func_object, schedule_node, trigger, now_str, trigger_info, OUT, TT)

                    elif run_as == "thread":
                        trigger_info = "cron_trigger-thread"
                        has_fired, has_error, TT = run_as_thread(func_object, schedule_node, trigger, now_str, trigger_info, OUT, TT)

                    elif run_as == "process":
                        trigger_info = "cron_trigger-process"
                        has_fired, has_error, TT = run_as_process(func_object, schedule_node, trigger, now_str, trigger_info, OUT, TT)

                    else:
                        has_error = True
                        msg = "Error while executing function '%s': %s %s" % (func_name, str(sys.exc_info()[0]), str(sys.exc_info()[1]))
                        s.set("single_trigger_status", "FAIL: %s: %s" % (now_str, msg))
                        TT.append([msg, time.time() - atime])
                        atime = time.time()
                        OUT(msg, logger='backend', print_stdout=True, level='error')

                except:
                    has_error = True
                    msg = "Error while executing function '%s': %s %s" % (func_name, str(sys.exc_info()[0]), str(sys.exc_info()[1]))
                    TT.append([msg, time.time() - atime])
                    atime = time.time()
                    logger.error(msg)

                if len(history) > MAX_CRON_HISTORY:
                    history = history[-MAX_CRON_HISTORY:]

                history.append(["OK", t_str, now_obj.isoformat()])
                history_str = json.dumps(history)
                s.set("cron_history", history_str)

                history_count_str = s.get('cron_history_count').strip()
                try:
                    history_count = int(history_count_str)
                except:
                    history_count = 0
                history_count += 1
                s.set("cron_history_count", str(history_count))

                msg = "cron trigger %s: executed function '%s' for node '%s' (%s) - history: %d, %s" % (
                    t_str, func_name, s_name, s_id, history_count, history_str)
                TT.append([msg, time.time() - atime])
                atime = time.time()
            except:
                has_error = True
                msg = "Error while preparing calling function '%s': %s %s" % (s, str(sys.exc_info()[0]), str(sys.exc_info()[1]))
                TT.append([msg, time.time() - atime])
                atime = time.time()
                OUT(msg, logger='backend', print_stdout=True, level='error')
                traceback.print_tb(sys.exc_info()[2], None, sys.stdout)

            msg = "     info cron trigger=%s, now=%s, time_overdue=%s, grace=%s" % (
                t_str, now_obj.isoformat(), str(time_overdue), str(grace))
            TT.append([msg, time.time() - atime])
            atime = time.time()

        else:
            has_error = True
            msg = "WARNING: function '%s' for node '%s' (%s) is not defined" % (func_name, s_name, s_id)
            TT.append([msg, time.time() - atime])
            atime = time.time()

    return has_fired, has_error, TT


def get_schedules_report(access=None):

    try:
        sched_root = tree.getRoot("schedules")
    except:
        res = ["could not find schedules root node"]
        return res

    schedules = [s for s in sched_root.getChildren() if s.type == "schedule"]
    if access:
        schedules = [s for s in schedules if access.hasAccess(s, "data")]

    if not schedules:
        res = ["could not find schedule nodes"]
        return res

    res = []
    res.append("%d schedule node(s) found:" % len(schedules))
    res.append("")

    for i, s in enumerate(schedules):
        res.append('-' * 20)
        res.append("%2d. schedule node %s (%s):" % (i + 1, str(s.id), s.name))
        res.append("")
        res.append("  attributes:")
        for k, v in s.items():
            if k not in ["function", "single_trigger", "single_trigger_status", "cron_dict", "cron_history", "cron_history_count"]:
                res.append("    %s = '%s'" % (k, v))
        res.append("")
        func = s.get("function")
        res.append("    function: %s (found: %s)" % (func, str(func in f_dict)))

        res.append("")
        single_trigger = s.get("single_trigger").strip()
        if single_trigger:
            res.append("    single_trigger: %s" % single_trigger)
            res.append("    single_trigger_status: %s" % s.get("single_trigger_status"))
            res.append("")

        res.append("")
        cron_dict = s.get("cron_dict").strip()
        if cron_dict:
            res.append("    cron_dict: %s" % cron_dict)
            res.append("    cron_history_count: %s" % s.get("cron_history_count"))
            cron_history_str = s.get("cron_history").strip()
            cron_history = json.loads(cron_history_str)
            res.append("    %d entries in cron_history" % len(cron_history))
            res.append("")
            for j, h in enumerate(cron_history):
                res.append("      cron_history[%2d]: %s: trigger: %s, run at: %s" % ((j, ) + tuple(h)))
            res.append("")
    return res


def thread_info(msg, key="info", msg_append=True):
    thread_ident = threading.currentThread().ident
    if msg_append:
        s = core.schedules.action_dict[thread_ident].get(key, "")
        core.schedules.action_dict[thread_ident][key] = s + msg
    else:
        core.schedules.action_dict[thread_ident][key] = msg


def mklink(nid):
    return "<a href='edit?id=%s&tab=schedule'>%s</a>" % (str(nid), str(nid))


def isActive(schedule):
    return bool(datetime.now().isoformat() < schedule.get('single_trigger') and not schedule.get('single_trigger_status').strip())


def getSchedulesForIds(nid_list, active_only=False, access=None, language=None):

    _nid2schedules = {}
    schedule2nids = {}

    nid_set = set(nid_list)
    schedule_list = [c for c in tree.getRoot("schedules").getChildren() if c.type == "schedule"]
    if access:
        schedule_list = [c for c in schedule_list if access.hasWriteAccess(c)]

    for schedule in schedule_list:

        single_trigger = schedule.get("single_trigger").strip()
        single_trigger_status = schedule.get("single_trigger_status").strip()

        now_str = datetime.now().isoformat()
        is_active = bool(now_str < single_trigger and not single_trigger_status.strip())
        if active_only and is_active:
            continue

        nodelist_str = schedule.get("nodelist")
        nodelist_ids = [nid.strip() for nid in nodelist_str.strip().split(",") if nid.strip()]
        nodelist_set = set(nodelist_ids)
        intersection = list(nid_set.intersection(nodelist_set))

        if intersection:
            if language:
                status = t(language, is_active and 'edit_schedule_schedule_active' or 'edit_schedule_schedule_not_active')
            else:
                status = t(language, is_active and 'active' or 'not_active')
            schedule2nids[str(schedule.id)] = {'nids': intersection, 'schedule': schedule, 'nids_all': list(
                nodelist_set), 'is_active': is_active, 'status': status}
            for nid in intersection:
                _nid2schedules[nid] = _nid2schedules.get(nid, []) + [schedule]

    nid2schedules = {}

    for nid in _nid2schedules.keys():
        node = None
        title = ""
        try:
            node = tree.getNode(nid)
            title = "'%s' - '%s'" % (node.name, node.type)
            no_such_node_error = False
        except:
            title = t(language, "edit_schedule_no_such_node")
            no_such_node_error = True
        if node and title and access and access.hasWriteAccess(node):
            schedule_list = [s for s in _nid2schedules[nid]]  # if isActive(s)]
            if schedule_list:
                nid2schedules[nid] = {'schedule_list': schedule_list, 'title': title, 'no_such_node_error': no_such_node_error, }

    nid2active_schedules = {}
    for nid in nid2schedules.keys():
        active_schedules_list = [s for s in _nid2schedules[nid] if isActive(s)]
        if active_schedules_list:
            nid2active_schedules[nid] = {}
            nid2active_schedules[nid]['schedule_list'] = active_schedules_list
            nid2active_schedules[nid]['title'] = nid2schedules[nid]['title']
            nid2active_schedules[nid]['no_such_node_error'] = nid2schedules[nid]['no_such_node_error']

    return nid2schedules, schedule2nids, nid2active_schedules


def deleteNodeIDsFromSchedule(node_id_list, schedule_id, access=None):

    errors = []

    if schedule_id:
        try:
            schedule = tree.getNode(schedule_id)
            if access and not access.hasWriteAccess(schedule):
                errors.append("edit_schedule_no_write_access_to_schedule")
        except:
            errors.append("edit_schedule_unexpected_no_such_schedule_node")
    else:
        errors.append("edit_schedule_unexpected_no_such_schedule_node")

    if errors:
        return errors

    nodelist = schedule.get('nodelist').strip().split(',')
    nodelist = [nid.strip() for nid in nodelist if nid.strip()]

    new_nodelist = []
    for nid in nodelist:
        if nid not in node_id_list:
            new_nodelist.append(nid)

    new_nodelist = ",".join(new_nodelist)
    schedule.set('nodelist', new_nodelist)

    return errors


def deleteSchedule(schedule_id, access=None):

    errors = []

    if schedule_id:
        try:
            schedule = tree.getNode(schedule_id)
            if access and not access.hasWriteAccess(schedule):
                errors.append("edit_schedule_no_write_access_to_schedule")

        except:
            errors.append("edit_schedule_unexpected_no_such_schedule_node")
    else:
        errors.append("edit_schedule_unexpected_no_such_schedule_node")

    if schedule.type not in ['schedule']:
        errors.append("edit_schedule_unexpected_no_such_schedule_node")

    if errors:
        return errors

    schedule_locked = schedule.get('system.lock')
    if schedule_locked.lower() in ['true', '1']:
        errors.append("edit_schedule_locked_schedule")

    try:
        schedules_root = tree.getRoot("schedules")
        schedules_root.removeChild(schedule)
    except:
        errors.append("edit_schedule_error_removing_schedule_node")

    return errors


def atextit_default(node, trigger=None, trigger_info=None):
    print '-> atexit_default:', node.id, node.name, trigger, trigger_info


def filter_access(fdict, access):
    if access.user.isAdmin():
        pass
        return fdict
    p = acl.p
    filtered_dict = {}
    for k in fdict.keys():
        acl_rule = fdict[k].acl_rule
        if acl_rule:
            res = p.parse(acl_rule).has_access(access, None)
            if res:
                filtered_dict[k] = fdict[k]
        else:
            filtered_dict[k] = fdict[k]
    return filtered_dict


class FormedFunction(object):

    def __init__(self):
        self.history = {}
        self.labels = {}
        self.fields = []
        self.field_descriptors = []
        self.function = None
        self.run_as = ["function", "thread", "process"][1]
        self.run_as_immediate = ["function", "thread", "process"][0]

        self.acl_rule = '( true )'
        # examples for acl rules
        # "( true )", "( iplist our_ips )", "( user Administrator )", "( NOT ( group Economics ) )"
        # "( date >= 01.07.2012 )", "( ( ip 123.123.123.123 ) OR ( ip 213.213.213.213 ) )"

        self.atexit = None
        self.longname = "default_longname for " + str(self.function)
        self.explanation = "default_explanation for " + str(self.function)

    def addLabel(self, lang_str, msgid, msgstr):

        if lang_str not in self.labels.keys():
            self.labels[lang_str] = []
        msgid_list = [x[0] for x in self.labels[lang_str]]

        if msgid in msgid_list:
            msgid_index = msgid_list.index(msgid)
            self.labels[lang_str][msgid_index] = (msgid, msgstr)
        else:
            self.labels[lang_str].append((msgid, msgstr))

    def addField(self, field):
        self.fields.append(field)

    def setLabels(self, label_dict):
        self.labels = label_dict

    def getLabels(self):
        return self.labels

    def setFields(self, field_list):
        self.fields = field_list

    def getFields(self):
        return self.fields

    def setFieldDescriptors(self, field_descr_list):
        self.field_descriptors = field_descr_list

    def getFieldDescriptors(self):
        return self.field_descriptors

    def registerLabels(self):
        import core.translation
        core.translation.addLabels(labels=self.labels)

    def t(self, lang_str, msgid):
        try:
            _list = [x[0] for x in self.labels[lang_str]]
            _index = _list.index(msgid)
            return self.labels[lang_str][_index][1]
        except:
            return msgid

    def getLongname(self, lang):
        return self.t(lang, self.longname)

    def getSortorderKey(self, lang):
        return self.getLongname(lang)

    def getExplanation(self, lang):
        return self.t(lang, self.explanation)

    def getMetafields(self, lang):

        ret = list()

        count = 0
        for field_type, field_name, field_label_msgid, field_validator_func in self.field_descriptors:
            count += 1
            field = tree.Node(field_name, "metafield")
            field.set("label", self.t(lang, field_label_msgid))
            field.set("type", field_type)
            field.__class__ = dict_type2class.get(field_type, m_text)

            if field_type in ["memo", "htmlmemo", "meta", "url", "text"] and not hasattr(field, "getValues"):
                field.getValues = lambda: ""

            field.label = self.t(lang, field_label_msgid)

            ret.append(field)

        return ret

    def getMetafieldDicts(self, lang):

        ret = list()

        count = 0
        for field_type, field_name, field_label_msgid, field_validator_func in self.field_descriptors:
            count += 1
            field = tree.Node(field_name, "metafield")
            field.set("label", self.t(lang, field_label_msgid))
            field.set("type", field_type)
            field.__class__ = dict_type2class.get(field_type, m_text)

            if field_type in ["memo", "htmlmemo", "meta", "url", "text"] and not hasattr(field, "getValues"):
                field.getValues = lambda: ""

            field.label = self.t(lang, field_label_msgid)

            d = {
                'field': field,
                'field_type': field_type,
                'field_name': field_name,
                'field_label_msgid': field_label_msgid,
                'field_explanation_msgid': field_label_msgid,
                'field_validator_func': field_validator_func,
                'lang': lang,
                'evaluation_error': False,
                'evaluation_error_msg': '',
                'value': '',
            }

            ret.append(d)

        return ret


def check_list(s, sep=None, test_func=lambda x: True):
    if not s.strip():
        return False
    if sep:
        test_list = [x.strip() for x in s.strip().split(sep)]
    else:
        test_list = [s.strip()]
    for x in test_list:
        if not test_func(x):
            return False
    return True


def isIntegers(s, sep=None):

    def test_func(x):
        try:
            int(x)
            return True
        except ValueError:
            return False

    res = check_list(s, sep=sep, test_func=test_func)

    return res


def isProbEmails(s, sep=";"):
    if not s.strip():
        return False
    if sep:
        test_list = [x.strip() for x in s.strip().split(sep)]
    else:
        test_list = [s.strip()]
    for x in test_list:
        if not (x.count("@") == 1 and len(x) > 4):
            return False
    return True


def isNotEmpty(s):
    if s:
        return True
    else:
        return False


# ###################################
# definitions of schedule functions
# ###################################


#
# definition for example function 'send_schedule_mail'
# one mail with information on the nodelist shall be sent
#


# parameters of the function
# format: [(type, name, label_msgid), ...]
send_schedule_mail_field_descriptors = [
    ("text", "attr_recipient", "send_schedule_mail_attribute_attr_recipient", isProbEmails),
    ("text", "attr_subject", "send_schedule_mail_attribute_attr_subject", None),
    ("memo", "attr_body", "send_schedule_mail_attribute_attr_body", isNotEmpty),
    ("text", "attr_sender", "send_schedule_mail_attribute_attr_sender", isProbEmails)
]


def getTALstr(s, context={}, language='en'):
    from mediatumtal import tal
    return tal.getTALstr(s, context, language=language)


def send_schedule_mail(node, trigger=None, now_str=None, trigger_info=None, OUT=None, TT=None, thread_name=None, func=None):

    recipient = str(node.get('attr_recipient'))
    subject = str(node.get('attr_subject'))
    body = str(node.get('attr_body'))
    sender = str(node.get('attr_sender'))

    def getAttribute(nid, attrname):
        try:
            n = tree.getNode(nid)
            return n.get(attrname)
        except:
            return ''

    def getItemDict(nid):
        try:
            n = tree.getNode(nid)
            return dict(n.items())
        except:
            return []

    nidlist = node.get('nodelist').strip().replace(",", ";").split(";")
    nidlist = [nid.strip() for nid in nidlist]

    context = {}
    context['datetime'] = datetime
    context['nidlist'] = nidlist
    context['getAttribute'] = getAttribute
    context['getItemDict'] = getItemDict
    context['now_str'] = now_str
    context['trigger'] = trigger
    context['trigger_info'] = trigger_info

    body = getTALstr(body, context)

    print "+++> this is 'utils.scheduleutils.send_schedule_mail'"
    print "     attr_recipient='%s'" % str(node.get('attr_recipient'))
    print "     attr_subject  ='%s'" % str(node.get('attr_subject'))
    print "     attr_body     ='%s'" % str(node.get('attr_body'))
    print "     attr_sender   ='%s'" % str(node.get('attr_sender'))
    print "<+++ leaving 'test_send_schedule_mail'"

    from . import mail
    mail.sendmail(sender, recipient, subject, body)

    return


c_send_schedule_mail = FormedFunction()
c_send_schedule_mail.function = send_schedule_mail
register_schedule_func("send_schedule_mail", send_schedule_mail)
c_send_schedule_mail.run_as = "thread"
c_send_schedule_mail.run_as_immediate = "thread"

send_schedule_mail_explain_de =\
    '''
Eine erste Funktion zum Versenden von Mail. Es wird eine Mail an eine vorgegebene (;-separierte) Adressenliste mit einem vorgegebenen Betreff gesandt.
Der Text der Mail kann ein TAL-Template sein. Im Kontext stehen die Liste 'nidlist' der ID's der Knotenauswahl und die Funktion
'getItemDict', die die Object-ID's auf ein Dictionary mit den Attributen abbildet, zur Auswahl.
'''

send_schedule_mail_explain_en =\
    '''
This function will send an email. The body may be a TAL template with the context variable 'nidlist' holding the id's of the objects selected in the editor
and the function 'getItemDict' mapping the object id's to a dictionary holding the attributes of the respective objects node.
'''

label_send_schedule_mail = {
    "de":
    [
        ("send_schedule_mail_attribute_attr_recipient", 'Zieladresse der Mail'),
        ("send_schedule_mail_attribute_attr_subject", 'Betreff der Mail (kann leer sein)'),
        ("send_schedule_mail_attribute_attr_body", 'Inhalt der Mail - sollte nicht leer sein '),
        ("send_schedule_mail_attribute_attr_sender", 'Absender der Mail - nicht leer'),
        ("send_schedule_mail_longname", 'Testfunktion: eMail versenden'),
        ("send_schedule_mail_explanation", send_schedule_mail_explain_de),

    ],
    "en":
    [
        ("send_schedule_mail_attribute_attr_recipient", '(;-separated) recipient addresses of the mail'),
        ("send_schedule_mail_attribute_attr_subject", 'Subject of the mail'),
        ("send_schedule_mail_attribute_attr_body", 'Body of the mail - should not be empty'),
        ("send_schedule_mail_attribute_attr_sender", 'Sender of the mail'),
        ("send_schedule_mail_longname", 'Test Function send mail - must not be empty'),
        ("send_schedule_mail_explanation", send_schedule_mail_explain_en),

    ]
}


c_send_schedule_mail.setLabels(label_send_schedule_mail)
c_send_schedule_mail.setFieldDescriptors(send_schedule_mail_field_descriptors)
c_send_schedule_mail.longname = "send_schedule_mail_longname"
c_send_schedule_mail.explanation = "send_schedule_mail_explanation"

fc_dict['send_schedule_mail'] = c_send_schedule_mail
