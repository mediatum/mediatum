# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from warnings import warn
from utils.date import format_date, parse_date, STANDARD_FORMAT, now
from sqlalchemy.orm import object_session


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

    @property
    def next_nid(self):
        warn("next_nid does not make sense anymore, returning None!")
        return None

    @property
    def prev_nid(self):
        warn("prev_nid does not make sense anymore, returning None!")
        return None

    def isActiveVersion(self):
        return True

    def getVersionList(self):

        warn("use self.tagged_versions", DeprecationWarning)
        return list(self.tagged_versions)

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
        return list(self.parents)

    def getFiles(self):
        warn("deprecated, use Node.files instead", DeprecationWarning)
        return list(self.files)

    def get(self, key, default=u""):
        """Returns a node attribute. Returns empty string by default if no value was found.
        Attributes prefixed with 'system.' in older mediaTUM versions still can be fetched
        with this method, but Node.system_attrs.get() without prefix should be used instead.
        Note that Node.system_attrs.get() returns None as default, not empty string.
        """
        if key.startswith("system."):
            warn("getting system. attribute with Node.get(), use Node.system_attrs.get()", DeprecationWarning)
            return self.system_attrs.get(key[7:], default if default != u"" else None)

        return self.attrs.get(key, default)

    def set(self, key, value):
        """Sets a node attribute.
        Attributes prefixed with 'system.' in older mediaTUM versions still can be set
        with this method, but Node.system_attrs[key] = value without prefix should be used instead.
        """
        if key.startswith("system."):
            warn("setting system. attribute with Node.set(), use Node.system_attrs[key] = value", DeprecationWarning)
            self.system_attrs[key[7:]] = value
        else:
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
        """nodes are always 'active'"""
        return self

    def getUpdatedDate(self, format=None):
        if format is None:
            format = STANDARD_FORMAT
        if self.get('updatetime'):
            return format_date(parse_date(self.get('updatetime')), '%d.%m.%Y, %H:%M:%S')
        if self.get('creationtime'):
            return format_date(parse_date(self.get('creationtime')), '%d.%m.%Y, %H:%M:%S')
        return ''

    def get_special(self, valuename, default=u""):
        '''Attribute getter with special cases for attributes of the node object; 'node.id', 'node.name'/'nodename', 'node.type', 'orderpos'
        This works like the old Node.get method.'''
        if valuename.startswith('node'):
            if valuename == 'nodename' or valuename == "node.name":
                return self.name
            elif valuename == 'node.id':
                return self.id
            elif valuename == 'node.type':
                return self.type
            elif valuename == 'node.orderpos':
                return self.orderpos
        else:
            return self.get(valuename, default)


    # access stuff

    def has_access(self, accesstype, req=None, user=None, ip=None, date=None):
        if user is not None or ip is not None or date is not None:
            return self.has_access_to_node_id(self.id, accesstype, user, ip, date)

        return self.req_has_access_to_node_id(self.id, accesstype, req)

    def has_read_access(self, req=None, user=None, ip=None, date=None):
        return self.has_access("read", req, user, ip, date)

    def has_write_access(self, req=None, user=None, ip=None, date=None):
        return self.has_access("write", req, user, ip, date)

    def has_data_access(self, req=None, user=None, ip=None, date=None):
        return self.has_access("data", req, user, ip, date)

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


class NodeVersionMixin(NodeMixin):
    """Override methods from NodeMixin for version objects of nodes
    """

    def isActiveVersion(self):
        return self.next is None

    def getActiveVersion(self):
        return self.version_parent

    @property
    def versions(self):
        return self.version_parent.versions
