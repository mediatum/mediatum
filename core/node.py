# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from warnings import warn

class NodeMixin(object):

    """Provides methods for simple node handling on top of the SQLAlchemy methods provided by Node.
    Contains legacy methods (camelCase) needed for old code which will be removed when they become unused.
    """

    @classmethod
    def get_all_subclasses(cls, filter_classnames=[]):
        """Returns all known subclasses of cls"""
        return [cls.__mapper__.polymorphic_map[n].class_ 
         for n in cls.__mapper__._acceptable_polymorphic_identities
         if n not in filter_classnames]    
        
    ### TODO: versions
    @property
    def next_nid(self):
        return None


    @property
    def prev_nid(self):
        return None


    def isActiveVersion(self):
        return True


    def getVersionList(self):
        return [self]


    def getLocalRead(self):
        return ""

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
        return self.attrs.get(key, default)

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
    
    def getActiveVersion(self):
        """TODO: implement me..."""
        return self

    def __repr__(self):
        return u"Node<{} '{}'> ({})".format(self.id, self.name, object.__repr__(self)).encode("utf8")

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
        