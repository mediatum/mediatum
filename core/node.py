# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""

from core.db.postgres import BaseNode
from core.db import database

db = database.getConnection()


class Node(BaseNode):

    """Provides methods for simple node handling on top of the SQLAlchemy methods provided by BaseNode.
    Contains legacy methods (camelCase) needed for old code which will be removed when they become unused.
    """

    __mapper_args__ = {
        'polymorphic_identity': 'node',
        'polymorphic_on': BaseNode.type
    }

    def __init__(self, name="", type="node", id=None):
        self.name = name
        self.type = type
        if id:
            self.id = id
        self.attributes = {}

    # legacy methods

    def getChild(self, name):
        return self.children.filter_by(name=name).one()

    def addChild(self, child):
        self.children.append(child)
        return child

    def getParents(self):
        return self.parents

    def getFiles(self):
        return self.files

    def get(self, key, default=""):
        value = self.attributes.get(key)
        if value:
            return value
        return default

    def set(self, key, value):
        self.attributes[key] = value

    def getName(self):
        return self.name

    def removeAttribute(self, key):
        del self.attributes[key]

    def getAccess(self, type):
        """ get a named access right (e.g. read, write, etc.)"""
        if type == "read":
            return self.read_access
        elif type == "write":
            return self.write_access
        elif type == "data":
            return self.data_access

    """ set a named access right (e.g. read, write, etc.)"""

    def setAccess(self, type, access):
        if type == "read":
            self.read_access = access
        elif type == "write":
            self.write_access = access
        elif type == "data":
            self.data_access = access

    def getOrderPos(self):
        return self.orderpos

    def setOrderPos(self, orderpos):
        self.orderpos = orderpos

    def getType(self):
        return "/".join([self.type, self.schema])

    def getChildren(self):
        return self.children.all()

    def getContainerChildren(self):
        return self.container_children.all()

    def getContentChildren(self):
        return self.content_children.all()

    def getContentType(self):
        if self.schema:
            return self.schema
        return self.type

    def __repr__(self):
        return "Node<{}: '{}'> ({})".format(self.id, self.name, object.__repr__(self))

    # some additional methods from dict

    def __contains__(self, key):
        return key in self.attributes\
            or key in ('node', 'node.name', "nodename", "node.id", "node.type", "node.orderpos")

    def __getitem__(self, key):
        if key not in self:
            raise KeyError(key)
        return self.get(key)

    def __iter__(self):
        """iter() thinks that a Node is iterable because __getitem__ is implemented.
        That behaviour is stupid (legacy...), so we have to state explicitly that this thing is not iterable!
        """
        raise TypeError("not iterable!")

    def __len__(self):
        """
        :returns: number of attributes
        """
        return len(self.attributes)

    def __nonzero__(self):
        """Some code in mediaTUM relies on the fact that Node objects are always true, like `if user:`
        which is really a check if the user is not None.
        This can fail now because __len__ == 0 means that the Node object is false.
        Such code should be fixed (=> use `if user is None`). In the meantime, we just say that Node is always true.
        """
        return True

    def __setitem__(self, key, value):
        self.set(key, value)

    def __delitem__(self, key):
        self.removeAttribute(key)

    def setdefault(self, key, value):
        """Same as dict.setdefault."""
        if key not in self:
            self.set(key, value)
            return value
        else:
            return self.get(key)


### additional node classes (root and its children)

class Root(Node):
    pass


class Users(Node):
    pass


class Mappings(Node):
    pass


class Metadatatypes(Node):
    pass


class Navigation(Node):
    pass


class UserGroups(Node):
    pass
