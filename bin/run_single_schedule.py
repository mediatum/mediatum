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
import os
import os.path
import sys
import logging

sys.path = ['.'] + sys.path


pid = os.getpid()

try:
    import psutil
    ppid = psutil.Process(pid).ppid
except:
    ppid = '-unknown-'

import utils
import utils.scheduleutils as su

logger = su.logger

log_error = su.LogWriter(logger, logging.ERROR)
stderr_orig = sys.stderr
sys.stderr = log_error

msg = 'scheduler process entered: pid=%s, ppid=%s, %s, args: %s' % (str(pid), str(ppid), __file__, str(sys.argv))
logger.info(msg)

schedule_id = sys.argv[1]

passed_schedule_id_type = None

try:
    int(schedule_id)
    passed_schedule_id_type = 'int'
except:
    try:
        if os.path.isfile(schedule_id):
            passed_schedule_id_type = 'file'
    except:
        pass

if not passed_schedule_id_type:
    msg = "run_single_schedule: cannot handle passed schedule identifier '%s', terminating process" % schedule_id
    logger.error(msg)
    sys.exit(0)

try:
    trigger = sys.argv[2]
except:
    trigger = None

tree = su.tree
schedules_root = tree.getRoot("schedules")

if passed_schedule_id_type == 'int':
    try:
        schedule = [s for s in [tree.getNode(schedule_id)] if s.type == 'schedule'][0]
    except:
        msg = "no such schedule: " + str(schedule_id)
        logger.error(msg)
        schedule = None
elif passed_schedule_id_type == 'file':
    import pickle
    sd = pickle.load(schedule_id)
    schedule = tree.getNode(sd['node_name'], sd['node_type'])
    for k, v in sd['items']:
        schedule.set(k, v)

if schedule:

    func_name = schedule.get('function')
    if func_name and func_name in su.fc_dict:
        f = su.fc_dict[func_name].function
        f(schedule, trigger)


msg = 'scheduler process leaving: pid=%s, ppid=%s, %s, args: %s' % (str(pid), str(ppid), __file__, str(sys.argv))
logger.info(msg)

sys.stderr = stderr_orig
