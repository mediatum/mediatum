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
import stat
import traceback
import sys
import os
import string
import hashlib
import re
import random

def esc(s):
    return s.replace("&", "&amp;").replace("\"", "&quot;").replace("<", "&lt;").replace(">", "&gt;")

def lightesc(s):
    return s.replace("<", "&lt;").replace(">", "&gt;")

def desc(s):
    return s.replace("&amp;", "&").replace("&quot;", "\"").replace("&lt;","<").replace("&gt;",">")
    
def u(s):  
    try:
        return s.encode("utf-8")
    except:
        try:
            s = unicode(s)
            return s.decode("latin-1").encode("utf-8")
        except:
            return s

def iso2utf8(s):
    return unicode(s,"latin-1").encode("utf-8")
    
def utf82iso(s):
    try:
        return unicode(s,"utf-8").encode("latin-1")
    except:
        return s

def splitpath(path):
    while path.endswith("/") or path.endswith("\\"):
        path = path[:-1]
    i = max(path.rfind("/"),path.rfind("\\"))
    if i>=0:
        return path[0:i],path[i+1:]
    else:
        return "",path

def splitfilename(path):
    try:
        i = path.rindex(".")
        return path[0:i],path[i+1:]
    except:
        return path,""

        
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
        if self.type=="intern":
            return "/?item="+self.filename
        elif self.type=="node":
            return "/?id="+self.filename
        elif self.type=="text":
            return ""
        return self.filename
            
    def getType(self):
        return self.type

    def getIcon(self):
        return self.icon
        
    def __str__(self):
        return "%s|%s|%s|%s" %(self.name, self.filename, self.type, self.icon)
    
    
def format_filesize(size):
    try:
        size = int(size)
    except:
        return size
    if size<1024:
        return "%d Byte" % size
    elif size<1048576:
        return "%d KByte" % (size/1024)
    elif size<1073741824:
        return "%d MByte" % (size/1048576)
    else:
        return "%d GByte" % (size/1073741824)

def get_hash(filename):
    try:
        fi = open(filename,"rb")
        s = fi.read()
        fi.close()
        return hashlib.md5(s).hexdigest()
    except IOError:
        return hashlib.md5("").hexdigest()

def get_filesize(filename):
    if os.path.exists(filename):
        stat = os.stat(filename)
        return stat[6]
    import core.config as config
    if os.path.exists(config.settings["paths.datadir"]+"/"+filename):
        stat = os.stat(config.settings["paths.datadir"]+"/"+filename)
        return stat[6]
    else:
        print "Warning: File",filename,"not found"
        return 0


normalization_items = {"chars":[("00e4", "ae"),\
                        ("00c4", "Ae"),\
                        ("00df", "ss"),\
                        ("00fc", "ue"),\
                        ("00dc", "Ue"),\
                        ("00f6", "oe"),\
                        ("00d6", "Oe"),\
                        ("00e8", "e"),\
                        ("00e9", "e")],\
                     "words":[]}

    
def normalize_utf8(s):
    global normalization_items
    
    s = s.lower()
    # Process special characters for search
    for key,value in normalization_items["chars"]:
        repl = unichr(int(key, 16)).encode("utf-8")
        s = s.replace(repl, value)
    return s
    
def replace_words(s):
    global normalization_items
    s = s.lower()
    # Processing word trees for search
    for key, value in normalization_items["words"]:
        s = re.sub(str(key), value, s)
    return s

import locale
def compare_utf8(s1,s2):
    return locale.strcoll(normalize_utf8(s1), normalize_utf8(s2))

    
def compare_digit(s1,s2):
    if int(s1)<int(s2):
        return -1
    return 1

class Option:
    def __init__(self, name="", shortname="", value="", imgsource="", optiontype=""):
        self.name = name
        self.shortname = shortname
        self.value = value
        self.imgsource = imgsource
        self.optiontype = optiontype

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
    
    
def isCollection(node):
    try:
        if node.type in["collection", "collections"]:
            return 1
        return 0
    except:
        return 0

def getCollection(node):
    def p(node):
        import core.tree
        if node.type == "collection" or node.type == "collections":
            return node
        for pp in node.getParents():
            n = p(pp)
            if n:
                return n
        return None
    collection = p(node)
    if collection is None:
        import core.tree
        collection = core.tree.getRoot("collections")
    return collection

def getAllCollections():
    l = []
    def f(l,node):
        for c in node.getChildren():
            if isCollection(c):
                l += [c]
                f(l, c)
    import core.tree
    f(l, core.tree.getRoot("collections"))
    return l

def isDirectory(node):
    #if node.type.startswith("directory"):
    if node.getContentType()=="directory" or node.isContainer():
        return 1
    else:
        return 0
        
def getDirectory(node):
    def p(node):
        import core.tree
        if node.type.startswith("directory"):
            return node
        for pp in node.getParents():
            n = p(pp)
            if n:
                return n
        return None
    directory = p(node)
    if directory is None:
        import core.tree
        directory = core.tree.getRoot("collections")
    return directory

def ArrayToString(pieces, glue=""):
    return string.join(pieces,glue)

def formatException():
    s = "Exception "+str(sys.exc_info()[0])
    info = sys.exc_info()[1]
    if info:
        s += " "+str(info)
    s += "\n"
    for l in traceback.extract_tb(sys.exc_info()[2]):
        s += "  File \"%s\", line %d, in %s\n" % (l[0],l[1],l[2])
        s += "    %s\n" % l[3]
    return s

def join_paths(p1,p2):
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
    string = string.replace("\n"," ") .replace("\r"," ") .replace("\t"," ")
    stringl = string.lower()
    pos = 0
    while pos < len(string):
        firstindex = 1048576
        firstword = None
        for word in words:
            i = stringl.find(word, pos)
            if i>=0 and firstindex > i:
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
    elif filename.endswith(".pdf"):
        mimetype = "application/pdf"
        type = "document"
    elif filename.endswith(".ps"):
        mimetype = "application/postscript"
        type = "document"
    elif filename.endswith(".zip"):
        mimetype = "application/zip"
        type = "zip"
    elif filename.endswith(".avi"):
        mimetype = "video/x-msvideo"
        type = "video"
    elif filename.endswith(".flv"):
        mimetype = "video/x-flv"
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

    else:
        mimetype = "other"
        type = "other"

    return mimetype, type


def formatTechAttrs(attrs):
    ret = {}
    for sects in attrs.keys():
        for item in attrs[sects].keys():
            ret[item]=attrs[sects][item]
    return ret

    
def splitname(fullname):
    fullname = fullname.strip()
    
    firstname=lastname=title=""

    if fullname[-1] == ')':
        pos = len(fullname)-1
        brackets = 1
        while pos>0:
            pos = pos - 1
            if fullname[pos]=='(':
                brackets = brackets - 1
            if fullname[pos]==')':
                brackets = brackets + 1
            if brackets < 1:
                break
        title = fullname[pos+1:-1]
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
    
    return title,firstname,lastname


# get missing html close tags
def tag_check(content):
    r = re.compile("<[^>]*>")
    tags = r.findall(content)
    res = []
    last = ""
    for tag in tags:
        if tag in ("<br>", "<br/>"):
            continue
        
        if len(res)>0:
            last = res[-1]
        else:
            last = ""
   
        if last==tag:
            res = res[:-1]
        else:
            res.append(tag.replace("<", "</"))
    res.reverse()
    return res  

#
# returns formated string for long text
#
def formatLongText(value, field):
    try:
        if len(value)>500:
            val = value[:500]
            for item in tag_check(value[:500]):
                if item.find("/")>0:
                    val += item
                else:
                    val = item+value
                
                
            return '<div id="'+field.getName()+'_full" style="display:none">'+value+'&nbsp;&nbsp;&nbsp;&nbsp;<a href="#" title="Text reduzieren" onclick="expandLongMetatext(\''+field.getName()+'\')">&laquo;</a></div><div id="'+field.getName()+'_more">'+val+'...&nbsp;&nbsp;&nbsp;&nbsp;<a href="#" title="gesamten Text zeigen" onclick="expandLongMetatext(\''+field.getName()+'\')">&raquo;</a></div>'
        else:
            return value
    except:
        return value
    
    
def checkString(string):
    """ Checks a string, if it only contains alphanumeric chars as well as "-" """
    result = re.match("([\w\-]+)", string)
    if result and result.group(0)==string:
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

    
def union(definition): # or
    if not definition:
        return []
    result1 = definition[0]
    result2 = definition[1]
    if type(result1)!=dict:
        result1 = dict(zip(result1,result1))
    if type(result2)!=dict:
        result2 = dict(zip(result2,result2))
    result1.update(result2)
    if type(definition[0])==dict:
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

    
def intersection(definition): # and
    if not definition: 
        return [] 
    if type(definition[0])!=dict:
        result1 = definition[0]
    else:
        result1 = definition[0].keys()

    if type(definition[1])!=dict:
        result2 = dict(zip(definition[1],definition[1]))
    else:
        result2 = definition[1]
    result = {}
    for a in result1:
        if a in result2:
            result[a]=a
    if type(definition[0])!=dict:
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
        if self.link=="":
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
    menus = re.split("\);",menustring)
    for m in menus:
        items = re.split("\(|;", m)
        for item in items:
            
            if items.index(item)==0 and item.startswith("menu"):
                # menu
                submenu = Menu(item) # do not optimize, submenu obj needed
                menu.append(submenu)
            else:
                # submenu
                if (item!=""):
                    submenu.addItem(item)
    return menu
    
        
def getFormatedString(s):
    l = ["b", "sub", "sup", "em"]
    for i in l:
        s = s.replace("&lt;"+i+"&gt;", "<"+i+">").replace("&lt;/"+i+"&gt;", "</"+i+">")
    return s

def mkKey():
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    s = ""
    for i in range(0,16):
        s += alphabet[random.randrange(0,len(alphabet)-1)]
    return s
    
    
if __name__ == "__main__":
    def tt(s):
        t,f,l = splitname(s)
        print "Title:",t,"| Vorname:",f,"| Nachname:",l
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

    print union([[1,2,3],[3,4,5]])
    print intersection([[1,2,3],[3,4,5]])
    print union([{1:1,2:2,3:3},{3:3,4:4,5:5}])
    print intersection([{1:1,2:2,3:3},{3:3,4:4,5:5}])
