import StringIO
import athana
import os
import utils.utils as utils
import utils.fileutils as fileutils
import xmlnode
import core.tree as tree

class MetaDataWriter(StringIO.StringIO):
    def __init__(self, node):
        StringIO.StringIO.__init__(self)
        self.node = node

    def close(self):
        s = self.getvalue()
        newnode = xmlnode.parseNodeXML(s)
        #for k,v in self.node.items():
        #    self.node.set(k, "")
        print "type",newnode.type
        for k,v in newnode.items():
            print "metadata",k,v
            self.node.set(k,v)

        # FIXME: this is logic for the local TUM university archive, and not universal
        if "/" in newnode.type and (newnode.getSchema() not in ["lt", "diss"]):
            self.node.setSchema(newnode.getSchema())
        else:
            if newnode.getContentType() == "image":
                self.node.setSchema("pub-image")
            elif newnode.getContentType() == "document":
                self.node.setSchema("pub-book")
        
        print "-> ", self.node.type
        
        self.node.event_metadata_changed()

class FileWriter:
    def __init__(self, node, filename):
        f,ext = os.path.splitext(filename)
        self.realname = filename
        self.filename = os.tmpnam()+ext
        self.file = open(self.filename, "wb")
        self.node = node

    def write(self, data):
        self.file.write(data)

    def close(self):
        self.file.close()
        filenode = fileutils.importFile(self.realname, self.filename)

        for f in self.node.getFiles():
            self.node.removeFile(f)
        self.node.addFile(filenode)
        if self.node.getContentType() == "directory" and filenode.type:
            self.node.setContentType(filenode.type)
        self.node.event_files_changed()


class collection_ftpserver:
    def __init__(self, collection):
        self.user = collection.get("ftp_user")
        self.passwd = collection.get("ftp_passwd")
        self.collection = collection
        self.dir = [collection]
        self.node = collection

    def has_user(self, username, password):
        print username, password, self.user, self.passwd
        if username == self.user and password == self.passwd:
            return collection_ftpserver(self.collection)
        else:
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
            if filename == "metadata.xml":
                result = self.node,"metadata"
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
        if filename=="metadata.xml":
            r = MetaDataWriter(self.node)
        else:
            r = FileWriter(self.node, filename)
        self.dir = olddir
        self.node = oldnode
        return r

    def open(self, path, mode):
        if "w" in mode:
            return self.open_for_write(path, mode)
        if path.endswith("/metadata.xml") or path=="metadata.xml":
            path,filename = utils.splitpath(path)
            olddir = self.dir
            oldnode = self.node
            if not self.cwd(path):
                raise IOError("No such file: "+path)
            xml = xmlnode.getSingleNodeXML(self.node)
            self.dir = olddir
            self.node = oldnode
            return StringIO.StringIO(xml)
        else:
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
            d = [self.collection]
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
            self.dir = [collection]
            self.node = collection
        return 1

    def listdir (self, path, long=0):

        olddir = self.dir
        oldnode = self.node

        if path:
            print "listdir in",path
            self.cwd(path)

        l = []
        for c in self.dir[-1].getChildren():
            l += ["drwxrwxrwx    1 1001     100          4096 Jan 10  2008 %s" % c.getName()]
        for f in self.dir[-1].getFiles():
            if not f.getType().startswith('tile'):
                l += ["-rw-rw-rw-    1 1001     100      %8d Jan 10  2008 %s" % (f.getSize(),f.getName())]
        if not self.dir[-1].isContainer():
            l += ["-rw-rw-rw-    1 1001     100          4096 Jan 10  2008 metadata.xml"]

        self.dir = olddir
        self.node = oldnode

        return athana.list_producer(l)
