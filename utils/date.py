# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import time
import calendar
import datetime


class DateTime:

    def __init__(self, year, month, day, hour, minute, second):
        self.year = year
        self.month = month
        self.day = day
        self.hour = hour
        self.minute = minute
        self.second = second
        self.has_year = year
        self.has_month = month
        self.has_day = day
        self.has_time = hour or minute or second
        self.has_hour = hour
        self.has_minute = minute
        self.has_second = second

    def split(self):
        return (self.year, self.month, self.day, self.hour, self.minute, self.second)

    def int(self):
        # for sorting
        return self.second + 60 * (self.minute + 60 * (self.hour + 24 * (self.day + 32 * (self.month + 366 * self.year))))

    def daynum(self):
        return self.year * 32 * 12 + self.month * 32 + self.day

    def weekday(self):  # 0=monday
        if self.year > 1970:
            return calendar.weekday(self.year, self.month, self.day)
        return -1

    def maxMonthDay(self):
        return calendar.monthrange(self.year, self.month)[1]

    def __str__(self):
        return format_date(self)

    def __lt__(self, other):
        """ Enamble the comparison 'less than (<)' """
        if self.year < other.year:
            return True
        elif self.year == other.year:
            if self.month < other.month:
                return True
            elif self.month == other.month:
                if self.day < other.day:
                    return True
        return False

    def add(self, seconds):

        def days2month(days, startday, startmonth):  # calculate new day, month and year
            l = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
            d = days + startday
            m = startmonth
            y = 0
            while d - l[(m - 1) % 12] > 0:
                d -= l[(m - 1) % 12]
                m += 1
                if m > 12:
                    y += 1
                    m %= 12
            return d, m, y

        d = DateTime(self.year, self.month, self.day, self.hour, self.minute, self.second)

        d.second += seconds
        seconds /= 60
        d.second %= 60
        d.minute += seconds % 60
        seconds /= 60
        d.minute %= 60
        d.hour += seconds % 24
        seconds /= 24
        d.hour %= 24
        d.day, d.month, _y = days2month(seconds, self.day, self.month)
        d.year += _y
        return d


def format_date(t=None, format=None):
    if t is None:
        t = now()
    if not format:
        return "%0.4d-%0.2d-%0.2dT%0.2d:%0.2d:%0.2d" % (t.year, t.month, t.day, t.hour, t.minute, t.second)
    elif format == "rfc822":  # e.g. for rss
        import datetime
        weekdayname = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        monthname = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        dn = weekdayname[datetime.date(t.year, t.month, t.day).weekday()]
        return "%s, %0.2d %s %0.4d %0.2d:%0.2d:%0.2d CET" % (dn, t.day, monthname[t.month], t.year, t.hour, t.minute, t.second)
    else:
        i = 0
        result = u""
        l = len(format)
        while i < l:
            if format[i] == '%':
                i = i + 1
                if format[i] == 'Y':
                    result += "%0.4d" % t.year
                elif format[i] == 'y':
                    result += "%0.2d" % (t.year % 100)
                elif format[i] == 'm':
                    result += "%0.2d" % t.month
                elif format[i] == 'd':
                    result += "%0.2d" % t.day
                elif format[i] == 'H':
                    result += "%0.2d" % t.hour
                elif format[i] == 'M':
                    result += "%0.2d" % t.minute
                elif format[i] == 'S':
                    result += "%0.2d" % t.second
                else:
                    raise ValueError('Invalid format: %' + format[i])
                i += 1
            elif format[i] in "dmyHMS":
                nr = 0
                c = format[i]
                while i < l and c == format[i]:
                    i += 1
                    nr = nr + 1
                val = 0
                if c == 'y':
                    val = t.year
                elif c == 'm':
                    val = t.month
                elif c == 'd':
                    val = t.day
                elif c == 'H':
                    val = t.hour
                elif c == 'M':
                    val = t.minute
                elif c == 'S':
                    val = t.second
                result += ("%%0.%dd" % nr) % val
            else:
                result += format[i]
                i += 1
        return result


def make_date(year, month, day, hour=0, minute=0, second=0):
    return DateTime(year, month, day, hour, minute, second)


def now():
    t = time.localtime(time.time())
    return DateTime(t[0], t[1], t[2], t[3], t[4], t[5])

STANDARD_FORMAT = '%Y-%m-%dT%H:%M:%S'


def parse_date(string, format=None):
    string = string.strip()
    if format is None:
        try:
            return parse_date(string, format=STANDARD_FORMAT)
        except:
            try:
                return parse_date(string, format='%Y-%m-%d')
            except:
                return parse_date(string, format='%d.%m.%YT%H:%M:%S')
    i = 0
    pos = 0
    slen = len(string)
    l = len(format)
    year, month, day, hour, minute, second = 0, 0, 0, 0, 0, 0
    hasyear = 0
    hasmonth = 0
    hasday = 0
    hastime = 0
    while i < l:
        if pos >= slen:
            raise ValueError('Unexpected end of value string: "' + string + '"')
        if format[i] == '%':
            i = i + 1
            if format[i] == 'Y':
                year = int(string[pos:pos + 4])
                hasyear = 1
                pos += 4
            elif format[i] == 'y':
                y = int(string[pos:pos + 2])
                if y > 50:
                    year = 1900 + y
                else:
                    year = 2000 + y
                hasyear = 1
                pos += 2
            elif format[i] == 'm':
                if string[pos:pos + 2].isdigit():
                    month = int(string[pos:pos + 2])
                    hasmonth = 1
                    pos += 2
                elif string[pos:pos + 1].isdigit():
                    month = int(string[pos:pos + 1])
                    hasmonth = 1
                    pos += 1
                else:
                    month = 0
            elif format[i] == 'd':
                if string[pos:pos + 2].isdigit():
                    day = int(string[pos:pos + 2])
                    hasday = 1
                    pos += 2
                elif string[pos:pos + 1].isdigit():
                    day = int(string[pos:pos + 1])
                    hasday = 1
                    pos += 1
                else:
                    day = 0
            elif format[i] == 'H':
                hour = int(string[pos:pos + 2])
                hastime = 1
                pos += 2
            elif format[i] == 'M':
                minute = int(string[pos:pos + 2])
                hastime = 1
                pos += 2
            elif format[i] == 'S':
                second = int(string[pos:pos + 2])
                hastime = 1
                pos += 2
            else:
                raise ValueError('Invalid format: %' + format[i])
            i = i + 1
        elif format[i] in "dmyYHMS":
            nr = 0
            c = format[i]
            while i < l and c == format[i]:
                i += 1
                nr = nr + 1

            if not string[pos:pos + nr].isdigit():
                nr -= 1

            val = int(string[pos:pos + nr])
            pos = pos + nr
            if c == 'y':
                year = val
                hasyear = 1
            elif c == 'm':
                month = val
                hasmonth = 1
            elif c == 'd':
                day = val
                hasday = 1
            elif c == 'H':
                hour = val
                hastime = 1
            elif c == 'M':
                minute = val
                hastime = 1
            elif c == 'S':
                second = val
                hastime = 1
        else:
            if not format[i] == string[pos]:
                raise ValueError('Char not matched: ' + format[i])
            i += 1
            pos += 1
    if pos < slen:
        raise ValueError("trailing characters: " + string[pos:])
    date = DateTime(year, month, day, hour, minute, second)
    if format != STANDARD_FORMAT:
        date.has_time = hastime
        date.has_year = hasyear
        date.has_month = hasmonth
        date.has_day = hasday
    if not validateDate(date):
        raise ValueError("invalid date: " + ustr(date))
    return date


def validateDate(d):
    if not d.year and not d.year == 0:
        return False

    if d.has_month:
        if d.month > 12 or d.month < 0:
            return False

    if d.has_day:
        if d.day < 0:
            return False
        if d.day > 31:
            return False

    if d.has_month and d.has_day:
        if d.month in (4, 6, 9, 11) and d.day > 30:
            return False
        elif d.has_year and d.month == 2:
            leapyear = (d.year % 4 == 0 and d.year % 100 != 0) or (d.year % 400 == 0)
            if ((leapyear and d.day > 29) or (not leapyear and d.day > 28)):
                return False

    if d.has_hour:
        if 0 > d.hour or 24 < d.hour:
            return False

    if d.has_minute:
        if 0 > d.minute or 60 < d.minute:
            return False

    if d.has_second:
        if 0 > d.second or 60 < d.second:
            return False

    return True

""" validate given date-string """


def validateDateString(value, format=None):
    try:
        d = parse_date(value, format)
    except ValueError:
        return False
    return validateDate(d)


def dt_fromiso(isoformat_datestring):
    """Convert datetime string in isoformat to datetime object
       :param isoformat_datestring: string formatted like datetime.isoformat()
    """
    return datetime.datetime.strptime(isoformat_datestring, "%Y-%m-%dT%H:%M:%S")
