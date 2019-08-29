"""
 mediatum - a multimedia content repository

 Copyright (C) 2007 Arne Seifert <seiferta@in.tum.de>
 Copyright (C) 2007 Matthias Kramm <kramm@in.tum.de>
 Copyright (C) 2011 Werner F. Neudenberger <neudenberger@ub.tum.de>

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
import rfc822
from utils.utils import nullcontext as _nullcontext
from utils.locks import named_lock as _named_lock


def date2string(t, formatstring=None):
    '''t: float value as returned by time.time()'''
    if formatstring in [None, 'tuple']:
        return time.localtime(t)[0:6]
    elif formatstring == 'rfc822':
        return rfc822.formatdate(t)
    else:
        return formatstring % time.localtime(t)[0:formatstring.count('%')]


DEFAULTMAXAGE = 3600 * 24  # one day


class Cache:

    '''entry format: [timestamp, total_updatecount, updatecount_this_key,
                      hitcount, refusedcount, timestamp_string, data]'''

    def __init__(self, maxcount=0, maxsize=0, verbose=False):
        self.maxcount = maxcount
        self.maxsize = maxsize
        self.lock = _named_lock('cache')
        self.entries = {}
        self.updatecount = 0
        self.hitcount = 0
        self.misscount = 0
        self.refusedcount = 0  # too old cache entries refused
        self.verbose = verbose

    def update(self, key, value):
        now = time.time()
        snow = date2string(now, '%04d-%02d-%02d-%02d-%02d-%02d')
        with self.lock:
            keys = self.entries.keys()
            if (len(keys) >= self.maxcount) and key not in keys:
                oldest_key = self.getOldestKey(lock=False)
                key_age = time.time() - self.entries[oldest_key][0]
                key_total_updatecount = self.entries[oldest_key][1]
                delete_result = self.deleteKey(oldest_key, lock=False)
                if self.verbose:
                    print 'cache update: deleted oldest key:', oldest_key, 'age: %.3f sec.' % key_age, key_total_updatecount
            self.updatecount += 1
            oldvalue = self.entries.setdefault(key, [now, self.updatecount, 0, 0, 0, snow, value])
            newvalue = [now, self.updatecount, oldvalue[2] + 1, oldvalue[3], oldvalue[4], snow, value]
            self.entries[key] = newvalue

    def retrieve(self, key, maxage=DEFAULTMAXAGE):
        now = time.time()
        with self.lock:
            if key in self.entries:
                oldvalue = self.entries[key]
                if (now - oldvalue[0]) <= maxage:
                    result_code = 'hit'
                    res = newvalue = oldvalue
                    newvalue[3] += 1
                    self.entries[key] = newvalue
                    self.hitcount += 1
                else:
                    result_code = 'refused'
                    newvalue = oldvalue
                    newvalue[4] += 1
                    self.entries[key] = newvalue
                    res = (now - oldvalue[0])
                    self.refusedcount += 1
            else:
                result_code = 'missed'
                res = []
                self.misscount += 1
        return result_code, res

    def report(self):
        now = time.time()
        snow = date2string(now, '%04d-%02d-%02d-%02d-%02d-%02d')

        with self.lock:
            keys = sorted(self.entries.keys())
            header = '|tupd,upd,hit,refused,date,key'.split(',')
            hformat = "%4s|%4s|%4s|%4s|%19s|%-s"
            res = hformat % tuple(header)
            hline = '\r\n|' + '-' * len(res)
            res += hline
            rformat = "\r\n|%4d|%4d|%4d|%7d|%s|%-s"

            for key in keys:
                res += rformat % tuple(self.entries[key][1:6] + [key])
            res += hline
        return res

    def getOldestKey(self, lock=True):
        with self.lock if lock else _nullcontext():
            pairs = [[self.entries[k][0:2]] + [k] for k in self.entries.keys()]
            if pairs:
                pairs.sort()
                res = pairs[0][-1]
            else:
                res = None
        return res

    def deleteKey(self, key, lock=True):
        with self.lock if lock else _nullcontext():
            try:
                del self.entries[key]
                res = 1
            except:
                res = 0
        return res

    def getKeys(self, lock=True):
        with self.lock if lock else _nullcontext():
            res = self.entries.keys()
        return res

    def getKeysCount(self, lock=True):
        with self.lock if lock else _nullcontext():
            res = len(self.entries.keys())
        return res

    def getTimestamp(self, key, lock=True):
        with self.lock if lock else _nullcontext():
            res = self.entries[key][0]
        return res

    # def getData(self, key, lock=True):
    #    if lock:
    #        self.lock.acquire()
    #    res = self.entries[key][-1]
    #    if lock:
    #        self.lock.release()
    #    return res

if __name__ == '__main__':

    t = time.time()
    t2 = t - 24 * 3600
    print 'now:      ', date2string(t, 'rfc822'), date2string(t, '%04d-%02d-%02d-%02d-%02d-%02d')
    print 'yesterday:', date2string(t2, 'rfc822'), date2string(t2, '%04d-%02d-%02d-%02d-%02d-%02d')

    c = Cache(maxcount=3, maxsize=10, verbose=True)
    from random import randint
    for i in range(5):
        c.update(randint(1000, 1010), 'test-' + ustr(i + 1))

    print c.retrieve(1007, 1000)
    print c.retrieve('test', 1000)

    print c.report()
