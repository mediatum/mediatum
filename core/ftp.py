import StringIO
import time
import athana
import os
import hashlib
import utils.utils as utils
import utils.fileutils as fileutils
import xmlnode
import core.tree as tree
import core.users as users
from utils.date import parse_date
import core.config as config


class FileWriter:
    def __init__(self, node, filename):
        f,ext = os.path.splitext(filename)
        self.realname = filename
        self.filename = filename
        self.file = open(self.filename, "wb")
        self.node = node

    def write(self, data):
        self.file.write(data)

    def close(self):
        self.file.close()
        f = fileutils.importFile(self.realname, self.filename, "ftp_")
        os.remove(self.filename)
        self.node.addFile(f)
        

class collection_ftpserver:
    def __init__(self, basecontainer=None, port=21, debug="testing"):
        #set initial values
        self.user = ""
        self.passwd = ""
        self.basecontainer = ""
        self.dir = [basecontainer]
        self.node = None
        self.port = port
        self.logging = debug
        print "base:", basecontainer
        if basecontainer: # use special container for collections
            self.user = basecontainer.get("ftp.user")
            self.passwd = basecontainer.get("ftp.passwd")
            self.basecontainer = basecontainer
            self.dir = [basecontainer]
            self.node = basecontainer
            print self.user, self.passwd

    def debug(self):
        if self.logging=="testing":
            return 1
        return 0
        
    def getPort(self):
        return self.port
        
    def setUser(self, username, password="", basecontainer=None):
        self.user = username
        self.passwd = password
        self.basecontainer = basecontainer
        self.dir = [basecontainer]
        self.node = basecontainer # homedirectory of user

    def has_user(self, username, password):
        if username==self.user and (hashlib.md5(password).hexdigest()==self.passwd or password==self.passwd):
            return collection_ftpserver(self.basecontainer, port=self.port, debug=self.logging)
        else:
            user = users.checkLogin(username, password)
            if user:
                self.setUser(username, password, users.getUploadDir(user))
                return collection_ftpserver(self.basecontainer, port=self.port, debug=self.logging)
        return None

    def isdir(self, path):
        olddir = self.dir
        oldnode = self.node
        result = self.cwd(path)
        self.dir = olddir
        self.node = oldnode
        return result

    def isfile(self, path):
        path,filename = utils.splitpath(path)
        olddir = self.dir
        oldnode = self.node
        result = self.cwd(path)
        if result:
            result = None
            for f in self.node.getFiles():
                if filename == f.getName():
                    result = self.node,f
        self.dir = olddir
        self.node = oldnode
        return result

    def getfile(self, path):
        ff = self.isfile(path)
        if not ff or not len(ff)==2:
            raise IOError("no such directory/file "+path)
        return ff

    def stat(self, path):
        node,f = self.getfile(path)
        time = 1209465429
        return (0, 0, 2052L, 1, 1000, 100, f.getSize(), time, time, time)

    def unlink(self, path):
        node,f = self.getfile(path)
        if f == "metadata":
            raise IOError("Can't delete file")
        else:
            if os.path.exists(f.retrieveFile()):
                os.remove(f.retrieveFile())
            node.removeFile(f)
    
    def mkdir(self, path):
        path,filename = utils.splitpath(path)
        olddir = self.dir
        oldnode = self.node
        if not self.cwd(path):
            raise IOError("no such directory: "+path)
        node = self.node
        self.dir = olddir
        self.node = oldnode
        node.addChild(tree.Node(filename, type="directory"))
    
    def rmdir(self, path):
        path,filename = utils.splitpath(path)
        olddir = self.dir
        oldnode = self.node
        if not self.cwd(path):
            raise IOError("no such directory: "+path)
        try:
            for subdir in self.node.getChildren():
                if subdir.getName() == filename:
                    self.node.removeChild(subdir)
        finally:
            self.dir = olddir
            self.node = oldnode

    def open_for_write(self, path, mode):
        path,filename = utils.splitpath(path)
        olddir = self.dir
        oldnode = self.node
        if not self.cwd(path):
            raise IOError("no such directory: "+path)
        filename = config.get("paths.tempdir") + filename
        r = FileWriter(self.node, filename)
        self.dir = olddir
        self.node = oldnode
        return r

    def open(self, path, mode):
        if "w" in mode:
            return self.open_for_write(path, mode)
        
        node,f = self.isfile(path)
        if not f:
            raise IOError("No such file: "+path)
        file = f.retrieveFile()
        return open(file, "rb")
    
    def current_directory (self):
        return "/" + ("/".join([d.getName() for d in self.dir[1:]]))

    def cwd(self, dir):
        d = self.dir
        if len(dir) and dir[0] == '/':
            d = [self.basecontainer]
            dir = dir[1:]
        for c in dir.split("/"):
            if not c or c==".":
                pass
            elif c == '..' and len(d):
                d = d[0:-1]
            else:
                if d[-1].hasChild(c):
                    d += [d[-1].getChild(c)]
                else:
                    return 0
        self.dir = d
        if len(self.dir):
            self.node = self.dir[-1]
        else:
            self.dir = [self.basecontainer]
            self.node = self.basecontainer
        return 1
        
    def cdup(self):
        if len(self.dir)>1:
            self.dir = self.dir[:-1]
            self.cwd("..")
            return 1
        return 0
        
    def rnfr(self, line):
        self.filefrom = line[1]
        return 1
        
    def rnto(self, line):
        if self.filefrom:
            # check directory
            for c in self.node.getChildren():
                if c.getName()==self.filefrom:
                    c.set("nodename", line[1])
                    del self.filefrom
                    return 1
            #check files
            for f in self.node.getFiles():
                if f.retrieveFile().split("/")[-1]==self.filefrom:
                    if not line[1].startswith("ftp_"):
                        line[1] = "ftp_" + line[1]
                    nname = ("/".join(f.retrieveFile().split("/")[:-1]) + "/"+ line[1]).replace(" ", "_")
                    if not os.path.exists(nname):
                        os.rename(f.retrieveFile(), nname)
                        self.node.removeFile(f)
                        f._path = ("/".join(f._path.split("/")[:-1]) + "/"+ line[1]).replace(" ", "_")
                        self.node.addFile(f)
                        del self.filefrom
                        return 1
        return 0

    def listdir (self, path, long=0):
        olddir = self.dir
        oldnode = self.node

        if path:
            self.cwd(path)

        l = []
        for c in self.dir[-1].getChildren():
            if c.getName().strip()!="" and c.isContainer():
                nodedate = c.get("creationtime")
                if nodedate:
                    t = parse_date(nodedate)
                    l += ["drwxrwxrwx    1 1001     100          4096 %d %d %d %s" % (t.month, t.day, t.year, c.getName())]
                else:
                    l += ["drwxrwxrwx    1 1001     100          4096 Jan 10  2008 %s" % c.getName()]
        for f in self.dir[-1].getFiles():
            if not f.getType().startswith('tile') and "ftp_" in f.retrieveFile() and os.path.exists(f.retrieveFile()):
                t = os.stat(f.retrieveFile())[8] # last modification date
                l += ["-rw-rw-rw-    1 1001     100      %8d %d %d  %d %s" % (f.getSize(), time.localtime(t)[1], time.localtime(t)[2], time.localtime(t)[0], f.getName())]
        self.dir = olddir
        self.node = oldnode

        return athana.list_producer(l)
