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


import sys
import os.path
import time
import thread
import logging

import core.tree as tree
import core.athana as athana
import core.schedule

from datetime import datetime


logg = logging.getLogger(__name__)


def OUT(msg, logger='backend', print_stdout=False, level='info'):
    # ignore logger and stdout arguments
    getattr(logg, level)(msg)
    

TT = []
action_dict = {}


def timetable_update(msg):
    TT.append([msg, time.time() - atime])
    atime = time.time()


def ensureSchedulesRoot():
    try:
        schedules = tree.getRoot('schedules')
        msg = "scheduler: root node 'schedules' (id=%s) found" % ustr(schedules.id)
        OUT(msg)

    except tree.NoSuchNodeError as e:
        schedules = tree.Node(name='schedules', type='schedules')
        root = tree.getRoot()
        root.addChild(schedules)
        msg = "scheduler: created root node 'schedules' (id=%s)" % ustr(schedules.id)
        OUT(msg)


timeline = []


try:
    import utils.scheduleutils as scheduleutils
except:
    if not os.path.basename(sys.argv[0]) == 'run_single_schedule.py':
        msg = '|' + '-' * 60 + '\n'
        msg += "| Error importing module 'scheduleutils': %s %s\n" % (ustr(sys.exc_info()[0]), ustr(sys.exc_info()[1]))
        msg += "| WARNING: Scheduler could not be started\n"
        msg += '|' + '-' * 60
        OUT(msg, logger='backend', print_stdout=True, level='error')

count = 0


def scheduler_thread():
    global count
    import utils.scheduleutils as scheduleutils
    if not time:
        return
    ensureSchedulesRoot()
    TRIGGER_COUNT = 0

    while True:

        count += 1
        TT = []
        HAS_FIRED = HAS_ERROR = False
        atime0 = atime = time.time()
        now_obj = datetime.now()
        now_str = now_obj.isoformat()  # example: '2012-05-29T13:15:17.557000'

        if athana.ATHANA_STARTED:

            if count % scheduleutils.TRIGGER_INTERVAL == 0:

                TRIGGER_COUNT += 1

                sched_root = tree.getRoot("schedules")
                try:
                    tree.remove_from_nodecaches(sched_root)
                    msg = "flushed schedules"
                    TT.append([msg, time.time() - atime])
                    atime = time.time()
                except TypeError:
                    msg = "scheduler thread failed to remove schedules root from cache"
                    OUT(msg, logger='backend', level='warning')

                sched_list = [c for c in sched_root.getChildren() if c.type == 'schedule']
                # to do: sort?

                msg = "%d schedule(s) found" % len(sched_list)
                TT.append([msg, time.time() - atime])
                atime = time.time()
                SCHEDULES_IMPORT_ERROR = False

                try:
                    reload(scheduleutils)
                    msg = "reloaded module utils.scheduleutils"
                    TT.append([msg, time.time() - atime])
                    atime = time.time()
                except:
                    msg = "Error reloading module 'scheduleutils': %s %s" % (ustr(sys.exc_info()[0]), ustr(sys.exc_info()[1]))
                    TT.append([msg, time.time() - atime])
                    atime = time.time()
                    OUT(msg, logger='backend', print_stdout=True, level='error')
                    SCHEDULES_IMPORT_ERROR = True

                if not SCHEDULES_IMPORT_ERROR:
                    interval_seconds = scheduleutils.SLEEP_INTERVAL * scheduleutils.TRIGGER_INTERVAL
                    OUT("scheduler_thread (interval: %s sec.): %s" % (ustr(interval_seconds), now_str))
                    now_obj = datetime.now()
                    now_str = now_obj.isoformat()

                    for s in sched_list:

                        has_fired, has_error, tt = scheduleutils.handle_single_trigger(s, now_str, OUT)
                        TT = TT + tt
                        atime = time.time()
                        if has_fired:
                            HAS_FIRED = True
                        if has_error:
                            HAS_ERROR = True
                        try:
                            has_fired, has_error, tt = scheduleutils.handle_cron_dict(s, now_obj, OUT)
                        except:
                            has_fired, has_error, tt = False, True, []
                        TT = TT + tt
                        atime = time.time()
                        if has_fired:
                            HAS_FIRED = True
                        if has_error:
                            HAS_ERROR = True
                    sys.stdout.flush()

        else:
            msg = 'scheduler: check no: %d: athana not yet started' % (count)
            OUT(msg, print_stdout=False)

        def OUT_TT(TT):
            msg = "scheduler: timetable (scheduleutils.DEBUG = '%s')\n|" % (scheduleutils.DEBUG) + '-' * 60 + '\n'
            msg += '| check no %d at %s:\n' % (TRIGGER_COUNT, now_str)
            for s, t in TT:
                msg = msg + '| %.3f: %s\n' % (t, ustr(s))
            msg += '| duration: %.3f sec.\n' % (time.time() - atime0)
            msg += '|' + '-' * 60

            OUT(msg)

        if scheduleutils.DEBUG:
            if TT:
                OUT_TT(TT)
        else:
            if (HAS_FIRED or HAS_ERROR) and TT:
                OUT_TT(TT)

        correction = int((time.time() - atime0) / scheduleutils.SLEEP_INTERVAL)
        count += correction

        time.sleep(scheduleutils.SLEEP_INTERVAL)


def startThread():
    import utils.scheduleutils as scheduleutils
    thread_id = thread.start_new_thread(scheduler_thread, ())
    t = (ustr(thread_id), datetime.now().isoformat(), ustr(scheduleutils.SLEEP_INTERVAL), ustr(scheduleutils.TRIGGER_INTERVAL))
    msg = "scheduler: started scheduler (thread_id='%s') thread at %s, SLEEP_INTERVAL = %s, TRIGGER_INTERVAL = %s" % t
    OUT(msg)


def getSchedules():
    schedules = tree.getRoot("schedules")
    children = [c for c in schedules.getChildren() if c.type == 'schedule']
    children = children.sort_by_name()  # sort by execution datetime ?
    return children


def getSchedule(id):

    if ustr(id).isdigit():
        try:
            node = tree.getNode(id)
            if node.type == "schedule":
                node.__class__ = core.schedule.Schedule
                return node
            else:
                return None
        except tree.NoSuchNodeError as e:
            return None
    else:
        schedules = tree.getRoot("schedules")
        try:
            schedule = schedules.getChild(id)
            schedule.__class__ = core.schedule.Schedule
            return schedule
        except tree.NoSuchNodeError as e:
            return None


def create_schedule(name, attr_dict={}):

    schedules = tree.getRoot("schedules")

    schedule = tree.Node(name=name, type="schedule")
    for k, v in attr_dict.items():
        schedule.set(k, v)
    schedules.addChild(schedule)

    SCHEDULES_TO_BE_READ = True
    schedules.set("SCHEDULES_TO_BE_READ", "1")

    return schedule


def update_schedule(id, name=None, attr_dict={}):
    schedule = getSchedule(id)
    if name is not None:
        schedule.setName(name)
    for k, v in attr_dict.items():
        schedule.set(k, v)
    return schedule


def sortSchedules():
    groups = tree.getRoot("usergroups").getChildren().sort_by_name()
    for g in groups:
        g.setOrderPos(groups.index(g))
