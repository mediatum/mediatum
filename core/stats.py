#!/usr/bin/python
"""
 mediatum - a multimedia content repository

 Copyright (C) 2009 Arne Seifert <seiferta@in.tum.de>

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

import os
import pickle
import re
import xml.parsers.expat
import logging
import glob
import codecs
import sys
import time
from sets import Set
import shutil

from core import db, Node
import core.config as config
from lib.geoip.geoip import GeoIP, getFullCountyName, MEMORY_CACHE
from utils.date import parse_date, format_date, now, make_date
from utils.utils import splitpath
from utils.fileutils import importFile
from array import array

q = db.query

EDIT = 1
DOWNLOAD = 2
FRONTEND = 3

class LogItem:

    download_pattern = [('/doc/',          '/doc/[0-9]+',          len('/doc/')),
                        ('/download/',     '/download/[0-9]+',     len('/download/')),
                        ('/file/',         '/file/[0-9]+',         len('/file/')),
                        ('/image/',        '/image/[0-9]+',        len('/image/')),
                        ('/fullsize?id=',  '/fullsize\?id=[0-9]+', len('/fullsize?id='))]

    def __init__(self, data, is_download=False):
        self.id = ""
        try:
            m = re.split(' INFO | - - \[| \] \"GET | HTTP/1.[01]\"', data)
            self.date, self.time = m[0][:-4].split(" ")
            self.ip = m[1]
            self.url = m[-2]
            self.data = data
            self.id = 0
            self.type = ""
            self.inttype = 0
            #self.country = ""

            if is_download:
                for pattern, pattern_regex, offset in self.download_pattern:
                    if self.url.startswith(pattern):
                        m = re.findall(pattern_regex, self.url)
                        if len(m) == 1:
                            self.id = int(m[0][offset:])
                            self.type = "download"
                            self.inttype = DOWNLOAD
                            break

            elif self.url.startswith("/edit"):  # edit
                m = re.findall('/edit.*[\?|\&]id=[0-9]*', self.url)
                if len(m) == 1:
                    m = re.findall('[\?|\&]id=[0-9]*', self.url)
                    if len(m) == 1:
                        self.id = int(m[0][4:])
                self.type = "edit"
                self.inttype = EDIT

            else:  # frontend
                m1 = re.findall('show_id=[0-9]*', self.url)
                if len(m1) == 1:
                    self.id = int(m1[0][8:])
                    self.type = "frontend"
                    self.inttype = FRONTEND
                else:
                    m2 = re.findall('^/[0-9]+', self.url)
                    if len(m2) == 1 and m2[0] == self.url:
                        self.id = int(m2[0][1:])
                        self.type = "frontend"
                        self.inttype = FRONTEND
                    else:
                        m3 = re.findall('[\?|\&]id=[0-9]*', self.url)
                        if len(m3) == 1:
                            self.id = int(m3[0][4:])
                            self.type = "frontend"
                            self.inttype = FRONTEND

            if self.id == 0:
                return None
        except:
            return None

    def getDate(self):
        return self.date

    def getTime(self):
        return self.time

    def getTimestampShort(self):
        return format_date(parse_date((self.getDate()), "yyyy-mm-dd"), "yyyy-mm")

    def getUrl(self):
        return self.url

    def getID(self):
        return self.id

    def isFrontend(self):
        if self.url.find("edit") < 1:
            return 1
        return 0

    def getType(self):
        return self.type

    def getIp(self):
        if " " in self.ip:
            ip = "".join(self.ip.split(":")[:-1]).split(" ")[-1]
        else:
            ip = "".join(self.ip.split(":")[:-1])

        if ip == 'unknown':
            ip = '127.0.0.1'

        return ip

    def is_google_bot(self):
        if self.ip.startswith('66.249'):
            return True
        else:
            return False

    def get_visitor_number(self):
        global visitor_num

        if self.ip.startswith('66.249'):
            return ip_table['google_bot']

        else:
            ip_no_port = self.getIp()
            if ip_no_port not in ip_table:
                ip_table[ip_no_port] = visitor_num
                visitor_num += 1

        return ip_table[ip_no_port]

    def get_visitor_number1(self, col_id):

        if self.ip.startswith('66.249'):
            return col_id.ip_table['google_bot']

        else:
            ip_no_port = self.getIp()
            if ip_no_port not in col_id.ip_table:
                col_id.ip_table[ip_no_port] = col_id.visitor_num
                col_id.visitor_num += 1

        return col_id.ip_table[ip_no_port]


class StatAccess:

    def __init__(self):
        self.date = ""
        self.time = ""
        self.visitor = ""
        self.id = ""
        self.country = ""

    def __str__(self):
        return ','.join([self.visitor, self.id, self.country])

    # def getIp(self):
    #     return "".join(self.ip.split(", ")[-1])


class StatisticFile:

    def __init__(self, filenode):
        self.items = []
        self.created = None
        self.access = None
        self.currentnodeid = ""

        if filenode:
            self.filenode = filenode
            self.filename = splitpath(filenode.retrieveFile())[1]

            self.period_year = int(self.filename.split("_")[2].split("-")[0])
            self.period_month = int(self.filename.split("_")[2].split("-")[1])
            self.type = self.filename.split("_")[3]

            if filenode.exists:
                with open(filenode.abspath, "r") as fi:
                    # expat only understands str, so we cannot use codecs here, just plain open()
                    p = xml.parsers.expat.ParserCreate()
                    p.StartElementHandler = lambda name, attrs: self.\
                        xml_start_element(name, attrs)
                    p.EndElementHandler = lambda name: self.xml_end_element(name)
                    p.CharacterDataHandler = lambda d: self.xml_char_data(d)
                    p.ParseFile(fi)

    def getPeriodYear(self):
        return self.period_year

    def getName(self, id):
        node = q(Node).get(id)

        if node is None:
            return id

        return node.name

    def getPeriodMonth(self):
        return self.period_month

    def getCreationDate(self):
        return self.created

    def getItems(self):
        return self.items

    def getIDs(self):
        ids = {}
        ret = []
        if len(self.items) == 0:
            ret.append((0, 0))
            return ret

        for item in self.items:
            if item.id not in ids:
                ids[item.id] = 0
            ids[item.id] += 1

        for k in ids:
            ret.append((k, ids[k]))

        ret.sort(lambda x, y: cmp(y[1], x[1]))
        return ret

    # statistic for day
    def getProgress(self, type=""):
        items = {}
        if len(self.items) == 0:
            items[0] = {"items": {}, "max": 0, "max_p": 0, "max_u": 0}
            return items

        # fill items in structure
        if type == "":
            for i in range(1, parse_date(self.items[0].date, "yyyy-mm-dd").maxMonthDay() + 1):
                items[i] = {"items": []}

            for item in self.items:
                day = parse_date(item.date, "yyyy-mm-dd").day
                items[day]["items"].append(item)

        elif type == "day":
            for i in range(0, 8):
                items[i] = {"items": []}

            for item in self.items:
                weekday = parse_date(item.date, "yyyy-mm-dd").weekday()
                items[weekday + 1]["items"].append(item)

        elif type == "time":
            for i in range(0, 25):
                items[i] = {"items": []}

            for item in self.items:
                hour = parse_date(item.time, "HH:MM:SS").hour
                items[hour + 1]["items"].append(item)

        elif type == "country":
            for item in self.items:
                c = item.country
                if c == "":
                    c = "n.a."
                if c not in items.keys():
                    items[c] = {}
                    items[c]["items"] = []
                items[c]["items"].append(item)

            items[c]["items"].sort()

        max = 0  # maximum of progress
        max_p = 0  # maximum of pages
        max_u = 0  # maximum users
        for key in items:
            ids = {}
            visitors = {}
            if max <= len(items[key]["items"]):
                max = len(items[key]["items"])

            for item in items[key]["items"]:  # different pages
                if item.id not in ids.keys():
                    ids[item.id] = 0
                ids[item.id] += 1
            items[key]["different"] = ids

            if max_p <= len(ids):
                max_p = len(ids)

            for item in items[key]["items"]:  # different visitors
                if item.visitor not in visitors.keys():
                    visitors[item.visitor] = 0
                visitors[item.visitor] += 1
            items[key]["visitors"] = visitors

            if len(visitors) > max_u:
                max_u = len(visitors)

        items[0] = {"items": {}, "max": max, "max_p": max_p, "max_u": max_u}  # deliver max-values on index 0
        return items

    def getCountryName(self, id):
        return getFullCountyName(id)

    def getWeekDay(self, day):
        dt = make_date(self.period_year, self.period_month, day)
        return dt.weekday()

    def xml_start_element(self, name, attrs):
        if name == "nodelist":
            if "created" in attrs.keys():
                self.created = parse_date(attrs["created"], "yyyy-mm-dd HH:MM:SS")

        elif name == "node":
            if "id" in attrs.keys():
                self.currentnodeid = attrs["id"].encode("utf-8")

        elif name == "access":
            self.access = StatAccess()
            self.access.id = self.currentnodeid

            for key in attrs:
                if key == "date":
                    self.access.date = attrs[key].encode("utf-8")
                elif key == "time":
                    self.access.time = attrs[key].encode("utf-8")
                elif key == "visitor_number":
                    self.access.visitor = attrs[key].encode("utf-8")
                elif key == "country":
                    self.access.country = attrs[key].encode("utf-8")

    def xml_end_element(self, name):
        if name == "access":
            self.items.append(self.access)

    def xml_char_data(self, d):
        pass


logdata = {}
logitem_set = Set()
ip_table = {'google_bot': 1}
visitor_num = 2
count = 0


def readLogFiles(period, fname=None):
    """
    read the logfile fname and create a list of accesses
    :param period: format yyyy-mm
    :param fname: optional logfile name, default <period>.log
    :return: list of accesses
    """
    global logdata
    global logitem_set
    path = config.get("logging.path")
    files = []

    if not fname:
        if len(logdata) != 0:
            return logdata

        for name in glob.glob(path + '[0-9]*-[0-9]*.log'):
            if period in name:
                files.append(name)
    else:
        files.append(fname)
        print "using given filename", fname

    list = []
    line_count = 0
    time0 = time.time()
    prog = re.compile("/[0-9]+ ")
    for file in files:
        print "reading logfile", file
        if os.path.exists(file):
            # for line in codecs.open(file, "r", encoding='utf8'):
            for line in open(file, "r"):
                line_count += 1
                if line_count % 50000 == 0:
                    print "reading log file: %d lines processed" % line_count

                create_info = False
                is_download = False
                idx = line.find('GET /')
                if idx > 0:
                    # ignore robots-access from mediatumtest
                    if line.find('129.187.87.37') >= 0:
                        continue
                    url = line[idx + 4:]
                    if url.find('change_language') >= 0 or url.find('result_nav') >= 0:
                        continue
                    if url.startswith('/doc/') or url.startswith('/download/') or url.startswith('/file/') or \
                            url.startswith('/image/') or url.startswith('/fullsize?id='):
                        create_info = True
                        is_download = True
                    elif "id=" in url:
                        create_info = True
                    else:
                        if prog.match(url):
                            create_info = True

                if create_info:
                    info = LogItem(line, is_download)
                    if not info or info.getID() <= 0 or info.getID() > 10000000:
                        continue

                    if info.getID() not in logitem_set:
                        logitem_set.add(info.getID())
                    list.append(info)

    time1 = time.time()
    print time1 - time0
    sorted_list = sorted(list, key=lambda item: item.getID())

    logdata = sorted_list
    return sorted_list

ip2c = None

class CollectionId:
    ip_table = None
    visitor_num = 0
    ids_set = None
    fin_frontend = fin_download = fin_edit = None
    files_open = False
    first_frontend = first_download = first_edit = True
    in_ids = False
    collection = None
    statfiles = None

    def __init__(self, ids_set, collection):
        self.ids_set = ids_set
        self.collection = collection
        self.ip_table = {'google_bot': 1}
        self.visitor_num = 2
        self.statfiles = []


def buildStatAll(collections, period="", fname=None):  # period format = yyyy-mm
    """
    build the statistic files with name stat_<collection_id>_yyyy-mm_<type> where type is in
    'frontend', 'download' or 'edit'
    :param collections: list of collections for which the statistic files should be build
                        if this is an empty list, all collections and their children are
                        fetched as an psql command
    :param period: period for which the statistic files should be build, format yyyy-mm
    :param fname: optional name of the logfile, default <period>.log
    :return: None
    """

    data = readLogFiles(period, fname)

    time0 = time.time()
    collection_ids = {}
    for collection in collections:
        print collection
        in_logitem_set = False
        items = [collection] + collection.all_children.all()
        ids_set = Set()
        for item in items:
            ids_set.add(item.id)
            if item.id in logitem_set:
                in_logitem_set = True

        if in_logitem_set:
            collection_ids[collection.id] = CollectionId(ids_set, collection)

    if not collections:
        # read all collections and its children with a single psql command which is much more faster
        # than the use of collection.all_children
        import core
        out = core.db.run_psql_command("select nid, id from node, noderelation where cid=id and" +
                                       " nid in (select id from node where type in ('collection', 'collections'))" +
                                       " order by nid",
                                       output=True, database=config.get("database.db"))
        lines = out.split('\n')
        last_collection = 0
        for line in lines:
            if line:
                collection_s, id_s = line.split('|')
                collection = int(collection_s)
                id = int(id_s)
                if last_collection != collection:
                    if last_collection:
                        if in_logitem_set:
                            collection_ids[last_collection] = CollectionId(ids_set, db.query(Node).get(last_collection))
                    in_logitem_set = False
                    ids_set = Set()
                    # add also collection itself
                    ids_set.add(collection)
                ids_set.add(id)
                if id in logitem_set:
                    in_logitem_set = True
                last_collection = collection

        if last_collection:
            if in_logitem_set:
                collection_ids[last_collection] = CollectionId(ids_set, db.query(Node).get(last_collection))

    time1 = time.time()
    print "time to collect all %d collections: %f" % (len(collection_ids), time1 - time0)

    # in buildStatAll_ for every collection 3 filedescriptors (frontend, download, edit) may be opened
    # to avoid running out of the available filedescriptors (currently 1024 per process)
    # buildStatAll_ is called multiple times with a collection chunk of lower than 300 collections
    collection_ids_keys = collection_ids.keys()
    collection_count = len(collection_ids_keys)
    collection_chunk = collection_count
    n = 1
    while collection_chunk > 300:
        n += 1
        collection_chunk = collection_count / n

    collection_chunk += 1
    start_idx = 0
    while start_idx < collection_count:
        end_idx = start_idx + collection_chunk
        print "start_idx:", start_idx, "end_idx:", end_idx
        buildStatAll_(collection_ids, collection_ids_keys[start_idx:end_idx], data, period, fname)
        start_idx = end_idx


def buildStatAll_(collection_ids, collection_ids_keys, data, period="", fname=None):  # period format = yyyy-mm

    # read data from logfiles
    def getStatFile(col_id, timestamp, type, period=period):
        f = None
        node = col_id.collection
        orig_file = None
        for file in node.getFiles():
            if file.getType() == u"statistic":
                try:
                    if file.getName() == u"stat_{}_{}_{}.xml".format(node.id, timestamp, type):
                        if timestamp == format_date(now(), "yyyy-mm") or timestamp == period:  # update current month or given period
                            # orig_file = file.retrieveFile()
                            if os.path.exists(file.retrieveFile()):
                                print 'removing %s' % file.retrieveFile()
                                os.remove(file.retrieveFile())
                                orig_file = file.retrieveFile()
                            # node.files.remove(file)
                            f = None
                            break
                        else:  # old month, do nothing
                            print 'old file doing nothing'
                            return None
                except:
                    return None
        if not f:
            # create new file
            f_name = config.get("paths.tempdir") + u"stat_{}_{}_{}.xml".format(node.id, timestamp, type)
            # create new file and write header:j
            print 'creating writing headers %s' % f_name
            f = codecs.open(f_name, "w", encoding='utf8')
            f.write('<?xml version="1.0" encoding="utf-8" ?>\n')
            f.write('<nodelist created="' + format_date(now(), "yyyy-mm-dd HH:MM:SS") + '">\n')

            if f_name not in col_id.statfiles:
                col_id.statfiles.append((f_name, orig_file))
            return f

    print "buildStatAll_ called for %d collections" % len(collection_ids_keys)

    gi = GeoIP(flags=MEMORY_CACHE)

    time0 = time.time()
    last_access = None
    count = 0
    for access in data:
        if (count % 10000) == 0:
            print "writing stat files: %d lines from %d processed: %d%%" % (count, len(data), count * 100 / len(data))
        count += 1

        if last_access and last_access.getID() == access.getID():
            pass
        else:
            for col in collection_ids_keys:

                col_id = collection_ids[col]
                if not col_id.first_frontend:
                    col_id.fin_frontend.write("\t</node>\n")
                    col_id.first_frontend = True
                if not col_id.first_download:
                    col_id.fin_download.write("\t</node>\n")
                    col_id.first_download = True
                if not col_id.first_edit:
                    col_id.fin_edit.write("\t</node>\n")
                    col_id.first_edit = True

                col_id.in_ids = access.getID() in col_id.ids_set

        last_access = access

        for col in collection_ids_keys:
            col_id = collection_ids[col]
            if not col_id.in_ids:
                continue

            if not col_id.files_open:
                col_id.fin_frontend = getStatFile(col_id, period, "frontend", period)
                col_id.fin_download = getStatFile(col_id, period, "download", period)
                col_id.fin_edit = getStatFile(col_id, period, "edit", period)
                col_id.files_open = True

            first = False
            if access.inttype == FRONTEND:
                fin = col_id.fin_frontend
                if col_id.first_frontend:
                    first = True
                    col_id.first_frontend = False
            elif access.inttype == DOWNLOAD:
                fin = col_id.fin_download
                if col_id.first_download:
                    first = True
                    col_id.first_download = False
            elif access.inttype == EDIT:
                fin = col_id.fin_edit
                if col_id.first_edit:
                    first = True
                    col_id.first_edit = False

            if first:
                fin.write('\t<node id="%d">\n' % access.getID())

            try:
                country_code = gi.country_code_by_name(access.getIp())
            except Exception as e:
                print access.getIp(), e
                country_code = ""
            fin.write('\t\t<access date="%s" time="%s" country="%s" visitor_number="%s" bot="%s"/>\n' %
                      (access.getDate(),
                       access.getTime(),
                       country_code,
                       access.get_visitor_number1(col_id),
                       access.is_google_bot()))


    for col in collection_ids_keys:
        col_id = collection_ids[col]
        if not col_id.first_frontend:
            col_id.fin_frontend.write("\t</node>\n")
        if not col_id.first_download:
            col_id.fin_download.write("\t</node>\n")
        if not col_id.first_edit:
            col_id.fin_edit.write("\t</node>\n")

        if col_id.files_open:
            col_id.fin_frontend.write("</nodelist>\n")
            col_id.fin_download.write("</nodelist>\n")
            col_id.fin_edit.write("</nodelist>\n")
            col_id.fin_frontend.close()
            col_id.fin_download.close()
            col_id.fin_edit.close()

    time1 = time.time()
    print "read collection: %f" % (time1 - time0)

    for col in collection_ids_keys:
        col_id = collection_ids[col]
        for file, orig_file in col_id.statfiles:

            if orig_file:
                destfile = os.path.join(config.get("paths.datadir"), orig_file)
                shutil.copyfile(file, destfile)
                print "copy %s to %s" % (file, destfile)
            else:
                print "importFile %s" % file
                statfile = importFile(file.split("/")[-1], file)
                if statfile:
                    statfile.filetype = u"statistic"
                    col_id.collection.files.append(statfile)
                    db.session.commit()

            try:
                os.remove(file)
            except:
                pass


if __name__ == "__main__":
    readLogFiles()
