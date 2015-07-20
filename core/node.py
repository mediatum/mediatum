# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from warnings import warn
from utils.date import format_date, parse_date, STANDARD_FORMAT, now


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

    @classmethod
    def get_class_for_typestring(cls, typestring):
        """Returns a class object for a given typestring.
        Typestrings are values from the Node.type attribute, always in lowercase.
        This is the "polymorphic identity" of the node subclass in SQLAlchemy.
        """
        mapper = cls.__mapper__.polymorphic_map[typestring]
        return mapper.class_

    @classmethod
    def get_classname_for_typestring(cls, typestring):
        """Returns a class name for a given typestring or empty string, if not found.
        Typestrings are values from the Node.type attribute, always in lowercase.
        This is the "polymorphic identity" of the node subclass in SQLAlchemy.
        """
        clazz = cls.get_class_for_typestring(typestring)
        return clazz.__name__

    # TODO: versions
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
        raise Exception("old acl stuff removed!")

    def setAccess(self, type, access):
        raise Exception("old acl stuff removed!")

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

    def getUpdatedDate(self, format=None):
        if format is None:
            format = STANDARD_FORMAT
        if self.get('updatetime'):
            return format_date(parse_date(self.get('updatetime')), '%d.%m.%Y, %H:%M:%S')
        if self.get('creationtime'):
            return format_date(parse_date(self.get('creationtime')), '%d.%m.%Y, %H:%M:%S')
        return ''

    # access stuff

    def has_access(self, accesstype, req=None):
        return self.req_has_access_to_node_id(self.id, accesstype, req)

    def has_read_access(self, req=None):
        return self.req_has_access_to_node_id(self.id, "read", req)

    def has_write_access(self, req=None):
        return self.req_has_access_to_node_id(self.id, "write", req)

    def has_data_access(self, req=None):
        return self.req_has_access_to_node_id(self.id, "data", req)

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
