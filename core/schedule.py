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
import logging
import core
import core.tree as tree

try:
    import utils.scheduleutils as su
except:
    pass

from datetime import datetime

if sys.version[0:3] < '2.6':
    import simplejson as json
else:
    import json


class Schedule(tree.Node):

    def __init__(self, name="<unbenannt>", dbid=None):
        tree.Node.__init__(self, name=name, type="schedule", dbid=None)

    def getCategoryName(self):
        return "Schedule"

    def getDatetime_str(self):
        return self.get("datetime_str")

    def setDatetime_str(self, s):
        self.set("datetime_str", s)

    def get_cron_dict(self):
        return json.loads(self.get("cron_dict"))

    def set_cron_dict(self, s):
        if type(s) == dict:
            self.set("cron_dict", json.dumps(s))
        elif type(s) == type(""):
            self.set("cron_dict", s)
        else:
            raise TypeError("Schedule.set_cron_dict: inadmissible type:" + str(type(s)))

    def get_iter_date(self, start_datetime_obj, granularity, lookahead=24 * 60, lookback=60):
        g = su.iter_date(start_datetime_obj, json.loads(self.get('cron_dict')), granularity, lookahead, lookback)
        return g

    def get_cron_triggers(self, start_datetime_obj, granularity=['hours', 'minutes', 'seconds'][1], lookahead=24 * 60, lookback=60, tostring=True):
        _error = None
        if type(start_datetime_obj) == type(""):
            start_datetime_obj = datetime.strptime(start_datetime_obj, "%Y-%m-%dT%H:%M:%S")

        cron_dict_str = self.get('cron_dict')

        if not cron_dict_str:
            cron_dict = {}
        else:
            try:
                cron_dict = json.loads(cron_dict_str)
            except:
                msg = "error decoding string to json for node '%s' (%s): %s" % (self.name, self.id, cron_dict_str)
                logging.getLogger('backend').error(msg)
                _error = msg
                cron_dict = {}
        if not cron_dict:
            return _error, []

        try:
            g = su.iter_date(start_datetime_obj, cron_dict, granularity, lookahead, lookback)

            if tostring:
                res = [x.isoformat() for x in g]
            else:
                res = [x for x in g]

        except:
            msg = "error building datetime generator for node '%s' (%s): %s" % (self.name, self.id, cron_dict_str)
            logging.getLogger('backend').error(msg)
            _error = msg
            return _error, []

        return _error, res


tree.registerNodeClass('schedule', Schedule)
