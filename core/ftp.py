import logging
import time
from . import athana
import os
import codecs
import hashlib
import utils.utils as utils
import utils.fileutils as fileutils
from random import random
from core import Node
import core.users as users
from utils.date import parse_date
from utils.utils import utf8_decode_escape
import core.config as config
from core import db
from contenttypes import Directory

logg = logging.getLogger(__name__)


class FileWriter:

    def __init__(self, node, filename):
        f, ext = os.path.splitext(filename)
        self.realname = filename
        self.filename = filename
        self.file = codecs.open(self.filename, "wb")
        self.node = node

    def write(self, data):
        self.file.write(data)

    def close(self):
        self.file.close()
        try:
            f = fileutils.importFile(self.realname, self.filename, "ftp_")
            os.remove(self.filename)
            self.node.files.append(f)
            db.session.commit()
        except:
            pass


class collection_ftpserver:

    def __init__(self, basecontainer=None, port=21, debug="testing"):
        # set initial values
        self.user = ""
        self.passwd = ""
        self.basecontainer = ""
        self.dir = [basecontainer]
        self.node = None
        self.port = port
        self.logging = "ftp"
        logg.info("collection_ftpserver base: %s", basecontainer)
        if basecontainer:  # use special container for collections
            self.user = basecontainer.get("ftp.user")
            self.passwd = basecontainer.get("ftp.passwd")
            self.basecontainer = basecontainer
            self.dir = [basecontainer]
            self.node = basecontainer

    def debug(self):
        if self.logging == "testing":
            return 1
        return 0

    def getPort(self):
        return self.port

    def setUser(self, username, password="", basecontainer=None):
        self.user = username
        self.passwd = password
        self.basecontainer = basecontainer
        self.dir = [basecontainer]
        self.node = basecontainer  # homedirectory of user

    def has_user(self, username, password):
        if username == self.user and (hashlib.md5(password).hexdigest() == self.passwd or password == self.passwd):
            return collection_ftpserver(self.basecontainer, port=self.port, debug="athana")
        else:
            user = users.checkLogin(username, password)
            if user:
                self.setUser(username, password, users.getUploadDir(user))
                return collection_ftpserver(self.basecontainer, port=self.port, debug="athana")
        return None

    def isdir(self, path):
        olddir = self.dir
        oldnode = self.node
        result = self.cwd(path)
        self.dir = olddir
        self.node = oldnode
        return result

    def isfile(self, path):
        path, filename = utils.splitpath(path)
        olddir = self.dir
        oldnode = self.node
        result = self.cwd(path)
        if result:
            result = None
            for f in self.node.files:
                if filename == f.base_name:
                    result = self.node, f
            for node in self.node.children:
                if filename.replace('(%s) ' % node.id, '') == node.name:
                    result = self.node, node
        self.dir = olddir
        self.node = oldnode
        return result

    def getfile(self, path):
        ff = self.isfile(path)
        if not ff or not len(ff) == 2:
            raise IOError("no such directory/file " + path)
        return ff

    def stat(self, path):
        node, f = self.getfile(path)
        time = 1209465429
        return (0, 0, 2052, 1, 1000, 100, f.size, time, time, time)

    def unlink(self, path):
        node, f = self.getfile(path)
        if f == "metadata":
            raise IOError("Can't delete file")
        elif isinstance(f, Node):
            parent = self.dir[0].parents[0]
            for subfolder in parent.children:
                if subfolder.name == 'Papierkorb':
                    subfolder.children.append(f)
                    node.children.remove(f)
                    break
        else:
            if os.path.exists(f.abspath):
                os.remove(f.abspath)
            node.files.remove(f)
        db.session.commit()

    def mkdir(self, path):
        path, filename = utils.splitpath(path)
        olddir = self.dir
        oldnode = self.node
        if not self.cwd(path):
            raise IOError("no such directory: " + path)
        node = self.node
        self.dir = olddir
        self.node = oldnode
        node.children.append(Directory(utf8_decode_escape(filename)))
        db.session.commit()


    def rmdir(self, path):
        path, filename = utils.splitpath(path)
        olddir = self.dir
        oldnode = self.node
        if not self.cwd(path):
            raise IOError("no such directory: " + path)
        try:
            for subdir in self.node.children:
                if subdir.name == filename:
                    self.node.children.remove(subdir)
        finally:
            self.dir = olddir
            self.node = oldnode
        db.session.commit()

    def open_for_write(self, path, mode):
        path, filename = utils.splitpath(path)
        olddir = self.dir
        oldnode = self.node
        if not self.cwd(path):
            raise IOError("no such directory: " + path)
        filename = config.get("paths.tempdir") + filename
        r = FileWriter(self.node, filename)
        self.dir = olddir
        self.node = oldnode
        return r

    def open(self, path, mode):
        if "w" in mode:
            return self.open_for_write(path, mode)

        node, f = self.isfile(path)
        if not f:
            raise IOError("No such file: " + path)
        if isinstance(f, Node):
            file = f.files[0].abspath
        else:
            file = f.abspath
        return codecs.open(file, "rb")

    def current_directory(self):
        return "/" + ("/".join([d.name for d in self.dir[1:]]))

    def cwd(self, dir):
        d = self.dir
        if len(dir) and dir[0] == '/':
            d = [self.basecontainer]
            dir = dir[1:]
        for c in dir.split("/"):
            if not c or c == ".":
                pass
            elif c == '..' and len(d):
                d = d[0:-1]
            else:
                if d[-1].children.filter_by(name=c).scalar():
                    d += [d[-1].children.filter_by(name=c).one()]
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
        if len(self.dir) > 1:
            self.dir = self.dir[:-1]
            self.cwd("..")
            return 1
        return 0

    def rnfr(self, line):
        self.filefrom = line[1]
        return 1

    def rnto(self, line):
        logg.debug('in rnto')
        if self.filefrom:
            # check if trying to move file into another folder
            if len(line[1].split('/')) > 1:
                stack = line[1].split('/')
                filename = stack.pop()
                new_parent = None

                if len(stack) == 1 and stack[0] == '':
                    new_parent = self.dir[0]
                else:
                    destination_dir = stack.pop()

                if not new_parent:
                    # find destination folder
                    for node in self.dir[0].all_children:
                        if node.name == destination_dir:
                            new_parent = node
                            break

                # find node object
                for node in self.node.children:
                    if node.name == filename.replace('(%s) ' % node.id, ''):
                        new_parent.children.append(node)
                        self.node.children.remove(node)
                        db.session.commit()
                        return 1

            # check directory
            for c in self.node.children:
                # sets the name of the node
                if c.name == self.filefrom.replace('(%s) ' % c.id, ''):
                    c.set("nodename", line[1].replace('(%s) ' % c.id, ''))
                    del self.filefrom
                    db.session.commit()
                    return 1

            # check files
            for f in self.node.files:
                if f.abspath.split("/")[-1] == self.filefrom:
                    if not line[1].startswith("ftp_"):
                        line[1] = "ftp_" + line[1]
                    nname = ("/".join(f.abspath.split("/")[:-1]) + "/" + line[1]).replace(" ", "_")
                    if not os.path.exists(nname):
                        os.rename(f.abspath, nname)
                        self.node.files.remove(f)
                        f.path = ("/".join(f.path.split("/")[:-1]) + "/" + line[1]).replace(" ", "_")
                        self.node.files.append(f)
                        del self.filefrom
                        db.session.commit()
                        return 1
        return 0

    def listdir(self, path, long=0):
        olddir = self.dir
        oldnode = self.node
        upload_dir = self.dir[0]

        if path:
            self.cwd(path)

        l = []

        # convert nodefiles to nodes
        for nodefile in self.dir[-1].files:
            if not nodefile.filetype.startswith('tile') and "ftp_" in nodefile.abspath and os.path.exists(nodefile.abspath):
                file_to_node(nodefile, upload_dir)

        # display folders and nodes
        for node in self.dir[-1].children:
            if node.name.strip() != "" and node.isContainer():
                nodedate = node.get("creationtime")
                if nodedate:
                    t = parse_date(nodedate)
                    l += ["drwxrwxrwx    1 1001     100          4096 %d %d %d %s" % (t.month,
                                                                                      t.day,
                                                                                      t.year,
                                                                                      node.name)]
                else:
                    l += ["drwxrwxrwx    1 1001     100          4096 Jan 10  2008 %s" % node.name]
            else:
                display_name = node.name
                if node.get('nodename'):
                    display_name = node.get('nodename')
                l += ["-rw-rw-rw-    1 1001      100         0 %d %d %d (%s) %s" % (1,
                                                                                    1,
                                                                                    2000,
                                                                                    node.id,
                                                                                    node.name)]
        # display any unconverted files
        for nodefile in self.dir[-1].files:
            if not nodefile.filetype.startswith('tile') and "ftp_" in nodefile.abspath and os.path.exists(nodefile.abspath):
                t = os.stat(nodefile.abspath)[8]  # last modification date
                l += ["-rw-rw-rw-    1 1001     100      %8d %d %d  %d %s" %
                      (nodefile.size, time.localtime(t)[1], time.localtime(t)[2], time.localtime(t)[0], nodefile.base_name)]

        self.dir = olddir
        self.node = oldnode

        return athana.list_producer(l)


def file_to_node(fileobj, upload_dir):
    '''
    Converts the File object in the upload_dir into a Node with the FileNode as an attachment
    @param fileobj: FileNode
    @param upload_dir: Node
    @return: Node if one was created
    '''

    home_dir = upload_dir.parents[0]
    file_type = fileobj.filetype

    if file_type == 'other' or file_type == 'zip':
        return

    path = fileobj.abspath.split('/')

    new_nodename = path.pop().replace('ftp_', '', 1)
    new_filename = '.'.join([hashlib.md5(unicode(random())).hexdigest()[0:8],
                             new_nodename.split('.')[-1]])
    path.append(new_filename)
    new_abspath = '/'.join(path)

    try:
        os.rename(fileobj.abspath, new_abspath)
        fileobj.path = new_abspath.replace(config.get('paths.datadir'), '')
    except:
        return

    schema = home_dir.get(u'system.ftp.{}'.format(file_type)).lstrip('/')
    if not schema:
        schema = 'file'

    content_class = Node.get_class_for_typestring(fileobj.filetype)
    new_node = content_class(utf8_decode_escape(new_nodename), schema=schema)

    upload_dir.files.remove(fileobj)
    fileobj.filetype = content_class.get_upload_filetype()
    new_node.files.append(fileobj)

    new_node.event_files_changed()
    upload_dir.children.append(new_node)
    db.session.commit()

    return new_node
