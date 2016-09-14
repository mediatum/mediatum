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
import cgi
import inspect
import logging
import traceback
import sys
import os
import string
import hashlib
import re
import random
import io
from warnings import warn
from urlparse import parse_qsl, urlsplit, urlunsplit
from urllib import quote, urlencode

#import xml.parsers.expat
from lxml import etree
from HTMLParser import HTMLParser

from .compat import iteritems
from .strings import ensure_unicode_returned


def esc(s):
    return cgi.escape(s, quote=True)


def esc2(s):
    return cgi.escape(s.replace(u"\"", u"'"))


def desc(s):
    return s.replace("&amp;", "&").replace("&quot;", "\"").replace("&lt;", "<").replace("&gt;", ">")


def u(s):
    warn("u is deprecated, use unicode objects!!!", DeprecationWarning)
    try:
        return s.encode("utf-8")
    except:
        try:
            s = unicode(s)
            return s.decode("latin-1").encode("utf-8")
        except:
            return s


def u2(s):
    warn("u2 is deprecated, use unicode objects!!!", DeprecationWarning)
    try:
        return s.encode("utf-8")
    except:
        try:
            s2 = unicode(s, 'utf-8')
            return s2.encode("utf-8")
        except:
            try:
                return s.decode('latin1').encode('utf-8')
            except:
                return s


def utf8_decode_escape(s):
    '''
    Returns the string if it is utf8 encoded, otherwise a string escaped version
    @param s: string
    @return: string
    '''
    try:
        s.decode('utf8')
        return s
    except:
        return s.encode('unicode-escape')


def iso2utf8(s):
    warn("use unicode objects!!!", DeprecationWarning)
    return unicode(s, "latin-1").encode("utf-8")


def utf82iso(s):
    warn("utf82iso is deprecated, use unicode objects!!!", DeprecationWarning)
    try:
        return unicode(s, "utf-8").encode("latin-1")
    except:
        return s


replacements = {'sub': {'regex': re.compile(r'(?<=\$_)(.*?)(?=\$)'),
                        'tex': '$_%s$',
                        'html': '<sub>%s</sub>'},
                'sup': {'regex': re.compile(r'(?<=\$\^)(.*?)(?=\$)'),
                        'tex': '$^%s$',
                        'html': '<sup>%s</sup>'}}


@ensure_unicode_returned
def modify_tex(string, option):
    """
    Swaps tex super and subscript markup ($^...$ and $_...$)
    for their html tag counterparts (<sub>...</sub> and <sup>...</sup>)

    @param string: string to be modified
    @param option: 'html' swaps tex for html tags or 'strip' nto remove tex markup
    """
    for tag in replacements.keys():
        matches = re.findall(replacements[tag]['regex'], string)
        for match in matches:
            if option == 'html':
                string = string.replace(replacements[tag]['tex'] % match,
                                        replacements[tag]['html'] % match)
            if option == 'strip':
                string = string.replace(replacements[tag]['tex'] % match,
                                        match)
    return unicode(string)


def splitpath(path):
    while path.endswith("/") or path.endswith("\\"):
        path = path[:-1]
    i = max(path.rfind("/"), path.rfind("\\"))
    if i >= 0:
        return path[0:i], path[i + 1:]
    else:
        return "", path


def splitfilename(path):
    try:
        i = path.rindex(".")
        return path[0:i], path[i + 1:]
    except:
        return path, ""


def findLast(string, char):
    # TODO
    """Finds the last occurrence of char in string and returns its index. If the char cannot be found, return -1"""
    return string.rfind(char)


def isnewer(path1, path2):
    try:
        l1 = os.stat(path1)
        l2 = os.stat(path2)
        return l1[8] >= l2[8]
    except:
        return 0


def isNumeric(s):
    try:
        i = float(s)
    except ValueError:
        return 0
    else:
        return 1


def float_from_gps_format(string):  # e.g [48, 214/25, 0]
    if string[0] == '[' and string[-1] == '[':
        string = string[1:-1]
        components = string.split(",")

        if len(components) != 3:
            return 0

        result = 0
        result += float_from_fraction(components[0])
        result += float_from_fraction(components[1]) / 60
        result += float_from_fraction(components[2]) / 3600
        return result
    return 0


def float_from_fraction(string):
    components = string.split("/")
    if len(components) == 1:
        return float(components[0])
    elif len(components) == 2:
        return float(components[0]) / float(components[1])
    return 0


class Link:

    def __init__(self, link, title, label, target="_self", icon="/img/blank.gif"):
        self.link = link
        self.title = title
        self.label = label
        self.target = target
        self.icon = icon

    def getTitle(self):
        return self.title


class CustomItem:

    def __init__(self, name, filename, type="intern", icon=""):
        self.name = name
        self.filename = filename
        self.type = type
        self.icon = icon

    def getName(self):
        return self.name

    def getLink(self):
        if self.type == "intern":
            return "/?item=" + self.filename
        elif self.type == "node":
            return "/?id=" + self.filename
        elif self.type == "text":
            return ""
        return self.filename

    def getType(self):
        return self.type

    def getIcon(self):
        return self.icon

    def __str__(self):
        return "%s|%s|%s|%s" % (self.name, self.filename, self.type, self.icon)


def format_filesize(size):
    try:
        size = int(size)
    except:
        return size
    if size < 1024:
        return "%d Byte" % size
    elif size < 1048576:
        return "%d KByte" % (size / 1024)
    elif size < 1073741824:
        return "%d MByte" % (size / 1048576)
    else:
        return "%d GByte" % (size / 1073741824)


def get_hash(filename):
    try:
        pathname = filename
        if not os.path.exists(pathname):
            import core.config as config
            pathname = os.path.join(config.settings["paths.datadir"], filename )
        fi = open(pathname, "rb")
        s = fi.read()
        fi.close()
        return hashlib.md5(s).hexdigest()
    except IOError:
        return hashlib.md5("").hexdigest()


def get_filesize(filename):
    try:
        if os.path.exists(filename):
            stat = os.stat(filename)
            return stat[6]
        import core.config as config
        pathname = os.path.join(config.settings["paths.datadir"], filename )
        if os.path.exists(pathname):
            stat = os.stat(pathname)
            return stat[6]
        else:
            return 0
    except:
        return 0


normalization_items = {"chars": [("00e4", "ae"),
                                 ("00c4", "Ae"),
                                 ("00df", "ss"),
                                 ("00fc", "ue"),
                                 ("00dc", "Ue"),
                                 ("00f6", "oe"),
                                 ("00d6", "Oe"),
                                 ("00e8", "e"),
                                 ("00e9", "e")],
                       "words": []}


def normalize_utf8(s):
    s = s.lower()
    # Process special characters for search
    for key, value in normalization_items["chars"]:
        repl = unichr(int(key, 16)).encode("utf-8")
        s = s.replace(repl, value)
    return s


def replace_words(s):
    s = s.lower()
    # Processing word trees for search
    for key, value in normalization_items["words"]:
        s = re.sub(ustr(key), value, s)
    return s

import locale


def compare_utf8(s1, s2):
    if not s1:
        s1 = ""
    if not s2:
        s2 = ""
    return locale.strcoll(normalize_utf8(s1), normalize_utf8(s2))


def compare_digit(s1, s2):
    if int(s1) < int(s2):
        return -1
    return 1


class Option:

    def __init__(self, name="", shortname="", value="", imgsource="", optiontype="", validation_regex=""):
        self.name = name
        self.shortname = shortname
        self.value = value
        self.imgsource = imgsource
        self.optiontype = optiontype
        self.validation_regex = validation_regex

    def getName(self):
        return self.name

    def setName(self, value):
        self.name = value

    def getShortName(self):
        return self.shortname

    def setShortName(self, value):
        self.shortname = value

    def getValue(self):
        return self.value

    def setValue(self, value):
        self.value = value

    def getImagesource(self):
        return self.imgsource

    def setImagesource(self, value):
        self.imagesource = value

    def getOptionType(self):
        return self.optiontype

    def setOptionType(self, value):
        self.optiontype = value

    def get_validation_regex(self):
        return self.validation_regex

    def set_validation_regex(self, value):
        self.validation_regex = value


def isCollection(node):
    warn("use isinstance(node, (Collection, Collections))", DeprecationWarning)
    from contenttypes import Collection, Collections
    return int(isinstance(node, (Collection, Collections)))


def getCollection(node):
    warn("use Node.get_collection()", DeprecationWarning)
    return node.get_collection()


def isDirectory(node):
    warn("use isinstance(node, Directory)", DeprecationWarning)
    from contenttypes import Directory
    return int(isinstance(node, Directory))


def getDirectory(node):
    warn("use Node.get_container()", DeprecationWarning)
    return node.get_container()


def ArrayToString(pieces, glue=""):
    return string.join(pieces, glue)


def formatException():
    s = "Exception " + ustr(sys.exc_info()[0])
    info = sys.exc_info()[1]
    if info:
        s += " " + ustr(info)
    s += "\n"
    for l in traceback.extract_tb(sys.exc_info()[2]):
        s += "  File \"%s\", line %d, in %s\n" % (l[0], l[1], l[2])
        s += "    %s\n" % l[3]
    return s


def join_paths(p1, p2):
    if p1.endswith("/"):
        if p2.startswith("/"):
            return p1[:-1] + p2
        else:
            return p1 + p2
    else:
        if p2.startswith("/"):
            return p1 + p2
        else:
            return p1 + "/" + p2


def highlight(string, words, left, right):
    string = string.replace("\n", " ") .replace("\r", " ") .replace("\t", " ")
    stringl = string.lower()
    pos = 0
    while pos < len(string):
        firstindex = 1048576
        firstword = None
        for word in words:
            i = stringl.find(word, pos)
            if i >= 0 and firstindex > i:
                firstword = word
                firstindex = i
        if firstindex == 1048576:
            break
        si = string.find(' ', firstindex)
        if si < 0:
            si = len(string)
        string = string[0:firstindex] + left + string[firstindex:si] + right + string[si:]
        pos = si + len(left) + len(right)
    return string


#
# mimetype validator
#
def getMimeType(filename):

    filename = filename.lower().strip()
    mimetype = "application/x-download"
    type = "file"
    if filename.endswith(".jpg") or filename.endswith(".jpeg"):
        mimetype = "image/jpeg"
        type = "image"
    elif filename.endswith(".gif"):
        mimetype = "image/gif"
        type = "image"
    elif filename.endswith(".png"):
        mimetype = "image/png"
        type = "image"
    elif filename.endswith(".bmp"):
        mimetype = "image/x-ms-bmp"
        type = "image"
    elif filename.endswith(".tif"):
        mimetype = "image/tiff"
        type = "image"
    elif filename.endswith(".tiff"):
        mimetype = "image/tiff"
        type = "image"
    elif filename.endswith(".svg"):
        mimetype = "image/svg+xml"
        type = "image"
    elif filename.endswith(".pdf"):
        mimetype = "application/pdf"
        type = "document"
    elif filename.endswith(".ps"):
        mimetype = "application/postscript"
        type = "document"
    elif filename.endswith(".zip"):
        mimetype = "application/zip"
        type = "zip"
    elif filename.endswith(".mp4"):
        mimetype = "video/mp4"
        type = "video"
    elif filename.endswith(".doc"):
        mimetype = "application/msword"
        type = "document"
    elif filename.endswith(".ppt"):
        mimetype = "application/mspowerpoint"
        type = "ppt"
    elif filename.endswith(".xml"):
        mimetype = "application/xml"
        type = "xml"
    elif filename.endswith(".mp3"):
        mimetype = "audio/mpeg"
        type = "audio"
    elif filename.endswith(".wav"):
        mimetype = "audio/x-wav"
        type = "audio"
    elif filename.endswith(".aif") or filename.endswith(".aiff"):
        mimetype = "audio/x-aiff"
        type = "audio"
    elif filename.endswith(".new"):
        mimetype = "text/plain"
        type = "news"
    elif filename.endswith(".bib"):
        mimetype = "text/x-bibtex"
        type = "bibtex"
    elif filename.endswith(".sur"):
        mimetype = "text/plain"
        type = "survey"

    else:
        mimetype = "other"
        type = "other"

    return mimetype, type


def formatTechAttrs(attrs):
    ret = {}
    for sects in attrs.keys():
        for item in attrs[sects].keys():
            ret[item] = attrs[sects][item]
    return ret


def splitname(fullname):
    fullname = fullname.strip()

    firstname = lastname = title = ""

    if fullname[-1] == ')':
        pos = len(fullname) - 1
        brackets = 1
        while pos > 0:
            pos = pos - 1
            if fullname[pos] == '(':
                brackets = brackets - 1
            if fullname[pos] == ')':
                brackets = brackets + 1
            if brackets < 1:
                break
        title = fullname[pos + 1:-1]
        fullname = fullname[:pos]

    fullname = fullname.strip()
    if "," in fullname:
        parts = fullname.split(",")
        lastname = parts[0].strip()
        firstname = ",".join(parts[1:]).strip()
    else:
        parts = fullname.split(" ")
        lastname = parts.pop().strip()
        firstname = " ".join(parts).strip()

    return title, firstname, lastname


#

class HTMLTextCutter(HTMLParser):

    """cutting text content of html snippet after cutoff
    """

    def __init__(self, cutoff=500, output=sys.stdout):
        self.cutoff = cutoff
        self.count = 0
        self.output = output

        self.in_style = 0
        self.in_script = 0

        self.has_cutted_tr = False
        self.is_cutted = False
        HTMLParser.__init__(self)

    def handle_starttag(self, tag, attrs):
        if tag.strip().lower() == 'style':
            self.in_style += 1
        if tag.strip().lower() == 'script':
            self.in_script += 1
        if tag.strip().lower() in ['tr', 'td'] and self.is_cutted:
            self.has_cutted_tr = True
            return
        self.output.write("<%s%s>" % (tag, ''.join([' %s="%s"' % (k, v) for k, v in attrs])))

    def handle_endtag(self, tag):
        if tag.strip().lower() == 'style':
            self.in_style -= 1
        if tag.strip().lower() == 'script':
            self.in_script -= 1
        if tag.strip().lower() in ['tr', 'td'] and self.has_cutted_tr:
            return
        self.output.write("</%s>" % tag)

    def handle_startendtag(self, tag, attrs):
        if self.is_cutted and (tag.strip().lower() in ['br']):
            self.output.write("")
        else:
            self.output.write("<%s%s/>" % (tag, ''.join([' %s="%s"' % (k, v) for k, v in attrs])))

    def handle_data(self, data):
        if self.in_script + self.in_style > 0:
            res = data
        elif self.count >= self.cutoff:
            res = ""
            if len(data) > len(res):
                self.is_cutted = True
        else:
            res = data[0:self.cutoff - self.count]
            self.count += len(res)
            if len(data) > len(res):
                self.is_cutted = True
        self.output.write(res)

    def handle_charref(self, name):
        if self.in_script + self.in_style > 0:
            self.output.write("&#%s;" % name)
        elif self.count >= self.cutoff:
            self.is_cutted = True
        else:
            self.count += 1
            self.output.write("&#%s;" % name)

    def handle_entityref(self, name):
        if self.in_script + self.in_style > 0:
            self.output.write("&%s;" % name)
        elif self.count >= self.cutoff:
            self.is_cutted = True
        else:
            self.count += 1
            self.output.write("&%s;" % name)

    def handle_comment(self, data):
        self.output.write("<!--%s-->" % data)

    def handle_decl(self, decl):
        self.output.write("<!%s>" % decl)

    def handle_pi(self, data):
        self.output.write("<?%s>" % data)

    def close(self):
        HTMLParser.close(self)


#
# returns formated string for long text
#

@ensure_unicode_returned(silent=True)
def formatLongText(value, field, cutoff=500):
    try:
        out = io.StringIO()
        p = HTMLTextCutter(cutoff, out)
        p.feed(value)
        p.close()
        if p.is_cutted:
            val = p.output.getvalue()
            val = val.rstrip()
            return u'<div id="' + field.getName() + '_full" style="display:none">' + value + '&nbsp;&nbsp;&nbsp;&nbsp;<a href="#" title="Text reduzieren" onclick="expandLongMetatext(\'' + field.getName() + '\');return false">&laquo;</a></div><div id="' + \
                field.getName() + '_more">' + val + '...&nbsp;&nbsp;&nbsp;&nbsp;<a href="#" title="gesamten Text zeigen" onclick="expandLongMetatext(\'' + \
                field.getName() + '\');return false">&raquo;</a></div>'
        else:
            return value
    except:
        return value


def checkString(string):
    """ Checks a string, if it only contains alphanumeric chars as well as "-" """
    result = re.match("([\w\-]+)", string)
    if result and result.group(0) == string:
        return True
    return False


def removeEmptyStrings(list):
    list2 = []
    for r in list:
        if r:
            list2 += [r]
    return list2


def clean_path(path):
    newpath = ""
    lastc = None
    for c in path:
        if c not in "/abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_-.0123456789 ":
            c = "_"
        if c == "." and lastc == ".":
            return "illegal_filename"
        if c == "/" and lastc == "/":
            return "illegal_filename"
        lastc = c
        newpath += c
    return newpath


def union(definition):  # or
    if not definition:
        return []
    result1 = definition[0]
    result2 = definition[1]
    if not isinstance(result1, dict):
        result1 = dict(zip(result1, result1))
    if not isinstance(result2, dict):
        result2 = dict(zip(result2, result2))
    result1.update(result2)
    if isinstance(definition[0], dict):
        return result1
    else:
        return result1.keys()


def isParentOf(node, parent):
    parents = node.getParents()
    if node == parent:
        return 1
    if parent in parents:
        return 1
    for p in parents:
        if isParentOf(p, parent):
            return 1
    return 0


def intersection(definition):  # and
    if not definition:
        return []
    if not isinstance(definition[0], dict):
        result1 = definition[0]
    else:
        result1 = definition[0].keys()

    if not isinstance(definition[1], dict):
        result2 = dict(zip(definition[1], definition[1]))
    else:
        result2 = definition[1]
    result = {}
    for a in result1:
        if a in result2:
            result[a] = a
    if not isinstance(definition[0], dict):
        return result.keys()
    else:
        return result


class EncryptionException(Exception):

    def __init__(self, value=""):
        self.value = value

    def __str__(self):
        return repr(self.value)


class OperationException(Exception):

    def __init__(self, value=""):
        self.value = value

    def __str__(self):
        return repr(self.value)


class FileException:
    pass


class Menu:

    def __init__(self, name, link="", target="_self"):
        self.name = name
        self.link = link
        self.target = target
        self.item = list()
        self.default = ""

    def getLink(self):
        if self.link == "":
            return "."
        return self.link

    def getString(self):
        return self.getName() + "(" + ";".join(self.getItemList()) + ")"

    def getName(self):
        return self.name

    def getId(self):
        return self.name.split("_")[-1]

    def addItem(self, itemname):
        self.item.append(itemname)

    def getItemList(self):
        return self.item

    def setDefault(self, name):
        self.default = name

    def getDefault(self):
        return self.default


def parseMenuString(menustring):
    menu = []
    submenu = None
    if menustring.endswith(")"):
        menustring = menustring[:-1]
    menus = re.split("\);", menustring)
    for m in menus:
        items = re.split("\(|;", m)
        for item in items:

            if items.index(item) == 0 and item.startswith("menu"):
                # menu
                submenu = Menu(item)  # do not optimize, submenu obj needed
                menu.append(submenu)
            else:
                # submenu
                if (item != ""):
                    submenu.addItem(item)
    return menu


def getFormatedString(s):
    for i in ["b", "sub", "sup", "em"]:
        s = s.replace("&lt;" + i + "&gt;", "<" + i + ">").replace("&lt;/" + i + "&gt;", "</" + i + ">")
    return s


def mkKey():
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    s = ""
    for i in range(0, 16):
        s += alphabet[random.randrange(0, len(alphabet) - 1)]
    return s


class Template(object):

    """
    Simple and fast templating system for '[att:xyz]' references.

    Examples::

        >>> t = Template('a [att:TEST] template for [att:TEST]ing')
        >>> print( t({'TEST': 'toast'}) )
        a toast template for toasting
        >>> print( t({}) )
        a  template for ing
    """
    split_at_vars = re.compile(r'\[att:([^]]*)\]').split

    def __init__(self, template_string):
        """
        Split the template string by its attribute references and
        remember where they are in the resulting list.
        """
        self.template_parts = self.split_at_vars(template_string)
        self.attribute_positions = xrange(1, len(self.template_parts), 2)

    def __call__(self, data_provider, lookup=None):
        """
        Interpolate the template using the content of the data
        provider (dict or MediaTUM tree node).
        :param lookup: function for getting attributes from `data_provider`, defaults to data_provider.get
        """
        if lookup is None:
            lookup = data_provider.get

        text_parts = self.template_parts[:]
        for i in self.attribute_positions:
            func = ""
            attribute_name = text_parts[i].strip()
            if "|" in attribute_name:
                parts = re.split('\||\:|\,', attribute_name)
                attribute_name = parts[0]
                func = parts[1:]
            if attribute_name:
                text_parts[i] = unicode(lookup(attribute_name)) or ''
                try:
                    if func[0] == "substring":
                        text_parts[i] = self._substring(text_parts[i], func[1:])
                    if func[0] == "split":
                        text_parts[i] = self._split(text_parts[i], func[1:])
                except:
                    pass
        return ''.join(text_parts)

    def _substring(self, s, attrs):
        try:
            if len(attrs) == 1:
                return s[int(attrs[0]):]
            elif len(attrs) == 2:
                return s[int(attrs[0]):int(attrs[1])]
        except:
            return s

    def _split(self, s, attrs):
        try:
            if len(attrs) == 2:
                return s.split(attrs[0])[int(attrs[1])]
        except:
            return s


def checkXMLString(s):
    try:
        etree.fromstring(s.encode('utf-8'))
        return 1
    except etree.XMLSyntaxError:
        return 0


def quote_uri(uri):
    """Quote path parts and query parameters of a URI and return the resulting URI.
    """
    parsed_uri = urlsplit(uri)
    path = "/".join(quote(s) for s in parsed_uri.path.split("/"))
    query = urlencode(parse_qsl(parsed_uri.query))
    quoted_uri = urlunsplit((parsed_uri.scheme, parsed_uri.netloc, path, query, parsed_uri.fragment))
    return quoted_uri


def funcname():
    '''returns name of the current function'''
    return inspect.stack()[1][3]


def callername():
    '''returns name of the calling function'''
    return inspect.stack()[2][3]


def get_user_id(req):
    import core.users as users
    user = users.getUserFromRequest(req)
    res = "userid=%r|username=%r" % (user.id, user.getName())
    return res


def log_func_entry(req, modname, functionname, s_arg_info, logger=logging.getLogger('editor')):
    msg = ">>> %s entering %s.%s: %s" % (
        get_user_id(req), modname, functionname, s_arg_info)
    logger.debug(msg)


def log_func_exit(req, modname, functionname, extra_data, logger=logging.getLogger('editor')):
    msg = "<<< %s exiting  %s.%s: %r" % (
        get_user_id(req), modname, functionname, extra_data)
    logger.debug(msg)


def dec_entry_log(func):
    from functools import wraps
    import inspect
    import traceback
    import sys
    from core.config import basedir


    @wraps(func)
    def wrapper(*args, **kwargs):
        argnames = func.func_code.co_varnames[:func.func_code.co_argcount]
        a = inspect.getargspec(func)
        if a.defaults:
            defaults = zip(a.args[-len(a.defaults):],a.defaults)
        else:
            defaults = []
        d = {
              #'argnames': argnames,
              #'func.func_code.co_varnames': func.func_code.co_varnames,
              #'args': args,
              #'kwargs': kwargs,
              'defaults': defaults,
             }
        arg_info = []
        for arg_name, value in zip(argnames, args[:len(argnames)]) + [("args", list(args[len(argnames):]))] + [("kwargs", kwargs)]:

            if ("%r" % value).find('.athana.http_request object') > 0:
                _v = "req.path=%r|req.params=%r" % (value.path, value.params)
                value = _v
            arg_info.append('%s=%r' % (arg_name, value))
        s_arg_info = ', '.join(arg_info)
        s_arg_info = s_arg_info + ("%r" % d)

        st = list(inspect.stack()[1])
        _caller_module = st[1].replace(basedir, '').replace('.pyc', '').replace('.py', '').replace('/', '.').replace('\\', '.')
        _caller_lineno = st[2]
        _callername = st[3]
        _callerline = st[4]
        caller_info1 = 'caller: %s.%s (LINE: %d): %r' % (_caller_module, _callername, _caller_lineno, _callerline)

        log_func_entry(args[0], func.__module__, func.__name__, s_arg_info + ', ' + caller_info1)

        res = apply(func, args, kwargs)

        extra_data = ("%r" % res)
        if len(extra_data) > 200:
            extra_data = extra_data[0:200] + ' ...'
        extra_data = 'result: ' + extra_data
        log_func_exit(args[0], func.__module__, func.__name__, extra_data)

        #print_info(prefix='--> %s.%s' % (func.__module__, func.__name__), prolog='IN ' * 9, epilog='OUT ' * 9, tracecount=250, exclude=[])
        # for later: try to retrieve exit line, log that too
        return res
    return wrapper


def make_repr(**args):
    """Class decorator which uses init params to create a human readable instance repr.
    Looks like: MyClass(arg1=value,arg2=value)
    """
    def _make_repr(cls):
        """
        :param cls: A class that defines an __init__ method.
        """
        init_args = cls.__init__.__func__.func_code.co_varnames[1:]
        arg_placeholder = ",".join(arg + "={" + arg + "!r}" for arg in init_args)
        tmpl = cls.__name__ + "(" + arg_placeholder + ")"

        def repr(self):
            return tmpl.format(**self.__dict__)

        cls.__repr__ = repr
        return cls
    return _make_repr


def utf8_encode_recursive(d):
    if isinstance(d, dict):
        return {k.encode("utf8"): utf8_encode_recursive(v) for k, v in iteritems(d)}
    elif isinstance(d, list):
        return [utf8_encode_recursive(v) for v in d]
    elif isinstance(d, unicode):
        return d.encode("utf8")
    return d


def find_free_port():
    """Returns a free local port"""
    import socket
    s = socket.socket()
    try:
        s.bind(("", 0))
        _, port = s.getsockname()
    finally:
        s.close()
    return port



if __name__ == "__main__":
    def tt(s):
        t, f, l = splitname(s)
        print "Title:", t, "| Vorname:", f, "| Nachname:", l
    tt("Hans Maier (Prof. Dr.)")
    tt("Hans Peter-Juergen Maier (Prof. Dr.)")
    tt("Hans Peter-Juergen Maier (Prof. Dr. (univ))")
    tt("Hans Peter-Juergen Maier (Prof. Dr. (Uni Berlin))")

    print clean_path("../../etc/passwd")
    print clean_path("../etc/passwd")
    print clean_path("test.txt")
    print clean_path("../test.txt")
    print clean_path("//etc/passwd")
    print clean_path("test^^.txt")

    print union([[1, 2, 3], [3, 4, 5]])
    print intersection([[1, 2, 3], [3, 4, 5]])
    print union([{1: 1, 2: 2, 3: 3}, {3: 3, 4: 4, 5: 5}])
    print intersection([{1: 1, 2: 2, 3: 3}, {3: 3, 4: 4, 5: 5}])
