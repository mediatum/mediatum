# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from warnings import warn

from sqlalchemy.ext.mutable import MutableDict

from core.database.postgres import BaseNode, t_nodemapping
from core import db

q = db.query

def _cte_subtree(node):
    t = q(t_nodemapping.c.cid).\
        filter(t_nodemapping.c.nid == node.id).\
        cte(name="subtree", recursive=True)

    return t.union_all(
        q(t_nodemapping.c.cid).
        filter(t_nodemapping.c.nid == t.c.cid)
    )


class Node(BaseNode):

    """Provides methods for simple node handling on top of the SQLAlchemy methods provided by BaseNode.
    Contains legacy methods (camelCase) needed for old code which will be removed when they become unused.
    """

    def __init__(self, name="", type="node", id=None, schema=None, attrs=None, orderpos=None):
        self.name = name
        if "/" in type:
            warn("use separate type and schema parameters instead of 'type/schema'", DeprecationWarning)
            type, schema = type.split("/")
        self.type = type
        self.attrs = MutableDict()
        if id:
            self._id = id
        if schema:
            self.schema = schema
        if attrs:
            self.attrs.update(attrs)
        if orderpos:
            self.orderpos = orderpos

    ### legacy methods

    @property
    def attributes(self):
        warn("deprecated, use Node.attrs instead", DeprecationWarning)
        return self.attrs

    def getChild(self, name):
        warn("deprecated, use Node.children.filter_by(name=name).one() instead", DeprecationWarning)
        return self.children.filter_by(name=name).one()

    def addChild(self, child):
        warn("deprecated, use Node.children.append() instead", DeprecationWarning)
        self.children.append(child)
        return child

    def getParents(self):
        warn("deprecated, use Node.parents instead", DeprecationWarning)
        return self.parents

    def getFiles(self):
        warn("deprecated, use Node.files instead", DeprecationWarning)
        return self.files

    def get(self, key, default=""):
        value = self.attrs.get(key)
        if value:
            return value
        return default

    def set(self, key, value):
        # warn("deprecated, use Node.attrs = "value" instead", DeprecationWarning)
        self.attrs[key] = value

    def getName(self):
        warn("deprecated, use Node.name instead", DeprecationWarning)
        return self.name

    def removeAttribute(self, key):
        warn("deprecated, use del Node.attrs[attrname] instead", DeprecationWarning)
        del self.attrs[key]

    def getAccess(self, type):
        """ get a named access right (e.g. read, write, etc.)"""
        if type == "read":
            warn("deprecated, use Node.read_access instead", DeprecationWarning)
            return self.read_access
        elif type == "write":
            warn("deprecated, use Node.write_access instead", DeprecationWarning)
            return self.write_access
        elif type == "data":
            warn("deprecated, use Node.data_access instead", DeprecationWarning)
            return self.data_access

    def setAccess(self, type, access):
        """set a named access right (e.g. read, write, etc.)"""
        if type == "read":
            warn("deprecated, use Node.read_access = new_read_access instead", DeprecationWarning)
            self.read_access = access
        elif type == "write":
            warn("deprecated, use Node.write_access = new_write_access instead", DeprecationWarning)
            self.write_access = access
        elif type == "data":
            warn("deprecated, use Node.data_access = new_data_access instead", DeprecationWarning)
            self.data_access = access

    def getOrderPos(self):
        warn("deprecated, use Node.orderpos instead", DeprecationWarning)
        return self.orderpos

    def setOrderPos(self, orderpos):
        warn("deprecated, use Node.orderpos = orderpos instead", DeprecationWarning)
        self.orderpos = orderpos

    def getType(self):
        warn("Node.getType() just returns self", DeprecationWarning)
        return self

    def getChildren(self):
        warn("deprecated, use Node.children instead", DeprecationWarning)
        return self.children

    def getContentChildren(self):
        warn("deprecated, use Node.content_children instead", DeprecationWarning)
        return self.content_children

    def getContentType(self):
        warn("deprecated, use Node.type instead", DeprecationWarning)
        return self.type

    @property
    def all_content_children(self):
        from contenttypes.default import ContentType
        subtree = _cte_subtree(self)
        query = q(ContentType).\
            join(t_nodemapping, Node.id == t_nodemapping.c.cid).\
            join(subtree, subtree.c.cid == t_nodemapping.c.nid)

        return query

    def all_children_by_query(self, query):
        subtree = _cte_subtree(self)
        query = query.\
            join(t_nodemapping, Node.id == t_nodemapping.c.cid).\
            join(subtree, subtree.c.cid == t_nodemapping.c.nid)
        return query

    def __repr__(self):
        return "Node<{}: '{}'> ({})".format(self.id, self.name, object.__repr__(self))

    # some additional methods from dict

    def __contains__(self, key):
        return key in self.attrs\
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
        :returns: number of attrs
        """
        return len(self.attrs)

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
