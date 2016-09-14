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

from sqlalchemy.orm.exc import NoResultFound

from core import db, Node
import core.config as config
from lib.geoip.geoip import GeoIP, getFullCountyName
from utils.date import parse_date, format_date, now, make_date
from utils.utils import splitpath
from utils.fileutils import importFile


q = db.query


class LogItem:

    def __init__(self, data):
        self.id = ""
        try:
            m = re.split(' INFO | - - \[| \] \"GET | HTTP/1.[01]\"', data)
            self.date, self.time = m[0][:-4].split(" ")
            self.ip = m[1]
            self.url = m[-2]
            self.data = data
            self.id = 0
            self.type = ""
            #self.country = ""

            if self.url.startswith("/fullsize"):  # download
                m = re.findall('/fullsize\?id=[0-9]*', self.url)
                if len(m) == 1:
                    self.id = m[0][13:]
                    self.type = "download"

            elif self.url.startswith("/edit"):  # edit
                m = re.findall('/edit.*[\?|\&]id=[0-9]*', self.url)
                if len(m) == 1:
                    m = re.findall('[\?|\&]id=[0-9]*', self.url)
                    if len(m) == 1:
                        self.id = m[0][4:]
                self.type = "edit"
            else:  # frontend
                m = re.findall('[\?|\&]id=[0-9]*', self.url)
                if len(m) == 1:
                    self.id = m[0][4:]
                    self.type = "frontend"

            if self.id == 0:
                return None
        except:
            return None

    def getDate(self):
        return self.date

    def getTime(self):
        return self.time

    def getTimestampShort(self):
        return format_date(parse_date(ustr(self.getDate()), "yyyy-mm-dd"), "yyyy-mm")

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
ip_table = {'google_bot': 1}
visitor_num = 2


def readLogFiles(period, fname=None):
    global logdata
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

    data = {}  # data [yyyy-mm][id][type]
    for file in files:
        print "reading logfile", file
        if os.path.exists(file):
            for line in codecs.open(file, "r", encoding='utf8'):
                if "GET" in line and "id=" in line:
                    info = LogItem(line)
                    if not info or (info and info.getID() == ''):
                        continue

                    if info.getTimestampShort() not in data.keys():
                        data[info.getTimestampShort()] = {}

                    if info.getID() not in data[info.getTimestampShort()].keys():
                        data[info.getTimestampShort()][info.getID()] = {"frontend": [], "edit": [], "download": []}
                    try:
                        data[info.getTimestampShort()][info.getID()][info.getType()].append(info)
                    except:
                        pass
    logdata = data
    return data

ip2c = None


def buildStat(collection, period="", fname=None):  # period format = yyyy-mm
    gi = GeoIP()
    logging.getLogger(__name__).info("update stats for node %s and period %s", collection.id, period)
    statfiles = []

    # read data from logfiles
    def getStatFile(node, timestamp, type, period=period):
        f = None
        for file in node.getFiles():
            if file.getType() == "statistic":
                try:
                    if file.getName() == u"stat_{}_{}_{}.xml".format(node.id, timestamp, type):
                        if timestamp == ustr(format_date(now(), "yyyy-mm")) or timestamp == period:  # update current month or given period
                            if os.path.exists(file.retrieveFile()):
                                print 'removing %s' % file.retrieveFile()
                                os.remove(file.retrieveFile())
                            node.removeFile(file)  # remove old file and create new
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
            if os.path.exists(f_name):
                f = codecs.open(f_name, "a", encoding='utf8')
            else:
                # create new file and write header:
                print 'creating writing headers %s' % f_name
                f = codecs.open(f_name, "w", encoding='utf8')
                f.write('<?xml version="1.0" encoding="utf-8" ?>\n')
                f.write('<nodelist created="' + ustr(format_date(now(), "yyyy-mm-dd HH:MM:SS")) + '">\n')

            if f_name not in statfiles:
                statfiles.append(f_name)
            return f

    def writeFooters():
        for file in statfiles:
            with codecs.open(file, "a", encoding='utf8') as f:
                f.write("</nodelist>\n")

    ids = []
    items = collection.getAllChildren()
    for item in items:
        ids.append(item.id)
    data = readLogFiles(period, fname)

    gi = GeoIP()

    for timestamp in data.keys():
        for id in data[timestamp].keys():
            if id in ids:
                for type in ["frontend", "edit", "download"]:
                    fin = getStatFile(collection, timestamp, type, period)
                    if fin and len(data[timestamp][id][type]) > 0:
                        fin.write('\t<node id="%s">\n' % ustr(id))
                        for access in data[timestamp][id][type]:
                            fin.write('\t\t<access date="%s" time="%s" country="%s" visitor_number="%s" bot="%s"/>\n' %
                                      (ustr(access.getDate()),
                                       ustr(access.getTime()),
                                       gi.country_code_by_name(access.getIp()),
                                       ustr(access.get_visitor_number()),
                                       ustr(access.is_google_bot())))
                        fin.write("\t</node>\n")
                        fin.close()

    for file in statfiles:
        with codecs.open(file, "a", encoding='utf8') as f:
            f.write("</nodelist>\n")

        statfile = importFile(file.split("/")[-1], file)
        if statfile:
            statfile.type = "statistic"
            collection.addFile(statfile)

        try:
            os.remove(file)
        except:
            pass

if __name__ == "__main__":
    readLogFiles()
