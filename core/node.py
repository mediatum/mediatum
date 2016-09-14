# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
import logging
from warnings import warn
from utils.date import format_date, parse_date, STANDARD_FORMAT
from utils.url import add_query_params_to_url


logg = logging.getLogger(__name__)


class NodeMixin(object):

    """Provides methods for simple node handling on top of the SQLAlchemy methods provided by Node.
    Contains legacy methods (camelCase) needed for old code which will be removed when they become unused.
    """

    #: how long may contents derived from this node be cached?
    cache_duration = 0

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
        return self.children.filter_by(name=unicode(name)).one()

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
            return self.system_attrs.get(key[7:], default)

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
        if key.startswith("system."):
            warn("use del Node.system_attrs[attrname] instead", DeprecationWarning)
            del self.system_attrs[key[7:]]
        else:
            warn("use del Node.attrs[attrname] instead", DeprecationWarning)
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

    @property
    def pretty_format_update_time(self):
        """XXX: move this somewhere else!"""
        if self.updatetime:
            return format_date(parse_date(self.updatetime), '%d.%m.%Y, %H:%M:%S')
        if self.creationtime:
            return format_date(parse_date(self.creationtime), '%d.%m.%Y, %H:%M:%S')
        return ''

    def _add_version_tag_to_url(self, url):
        if not self.isActiveVersion():
            url = add_query_params_to_url(url, {"v": self.tag})

        return url
    
    @property
    def updatetime(self):
        """
        For compatibility purposes. Old mediatum used an attribute called "updatetime" to store the update time.
        Now we can use the time from sqlalchemy-continuum if we want to know when the node was changed to its current state.
        """
        return self.get_special("updatetime")

    
    @property
    def updateuser(self):
        """
        For compatibility purposes. Old mediatum used an attribute called "updateuser" to store the name of the updating user.
        Now we can use the user id from sqlalchemy-continuum if we want to know who changed the node to its current state.
        Old mediatum displayed a readable name, so we do the same here. This doesn't have to be a unique name!
        """
        return self.get_special("updateuser")
    
    @property
    def creator(self):
        return self.get_special("creator")
    
    @property
    def creationtime(self):
        return self.get_special("creationtime")
    
    
    def get_special(self, valuename, default=u""):
        '''Attribute getter with special cases for attributes of the node object and update information:
         * 'node.id', 'node.name'/'nodename', 'node.type', 'orderpos'
         * 'updatetime', 'updateuser'
        This can be used like the old Node.get method.'''
        
        if valuename.startswith('node'):
            if valuename == 'nodename' or valuename == "node.name":
                return self.name
            elif valuename == 'node.id':
                return self.id
            elif valuename == 'node.type':
                return self.type
            elif valuename == 'node.orderpos':
                return self.orderpos
            
        elif valuename in ("updateuser", "updatetime", "creationtime", "creator"):

            # legacy: use value from attributes if present
            if valuename in self.attrs:
                return self.attrs[valuename]
             
            # future: use information from sqlalchemy-continuum
            if valuename in ("creationtime", "creator"):
                return getattr(self.versions[0], valuename) 

            if valuename in ("updateuser", "updatetime"):
                return getattr(self.versions[-1], valuename) 
            
        else:
            return self.get(valuename, default)

    def set_legacy_update_attributes(self, user):
        # XXX: We still set the update attributes as normal attributes like before. 
        # It'd be better to replace this by the transaction attributes provided by sqlalchemy-continuum.
        self.attrs["updateuser"] = user.getName()
        self.attrs["updatetime"] = format_date()
        
    # access stuff

    def has_access(self, accesstype, req=None, user=None, ip=None, date=None):
        """Checks if it's permitted to access this node with `accesstype`.
        There are 3 modes:

        * Nothing except the `accesstype` is passed: current request is used (must have request context). This is recommended.
        * `req != None`: use user and ip from request, current date to check permission
        * At least one of `user`, `ip` or `date` `is != None`: check permission with given values.
          Uses the following defaults when a value is None:

          * user: guest user
          * ip: 0.0.0.0
          * date: current date
        """
        if user is not None or ip is not None or date is not None:
            if req is not None:
                raise ValueError("has_access can only be called with a request instance or user/ip/date, but not both!")

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

    def __unicode__(self):
        if self.schema:
            typestr = self.type + "/" + self.schema
        else:
            typestr = self.type

        return u"# {} {} \"{}\"".format(self.id, typestr, self.name)

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
    def system_attrs(self):
        return self.version_parent.system_attrs

    @property
    def versions(self):
        return self.version_parent.versions
    
    @property
    def updatetime(self):
        # Migrated versions may contain a updatetime attribute that must be used instead because
        # transaction.issued_at is set to the migration time, not update time.
        legacy_updatetime = self.attrs.get("updatetime")
        if legacy_updatetime:
            return legacy_updatetime

        continuum_time = self.transaction.issued_at
        if continuum_time is not None:
            return format_date(continuum_time)
       
        return u"" 

    @property
    def creationtime(self):
        # Migrated versions may contain a creationtime attribute that must be used instead because
        # transaction.issued_at is set to the migration time, not creation time.
        legacy_updatetime = self.attrs.get("creationtime")
        if legacy_updatetime:
            return legacy_updatetime
        
        continuum_time = self.versions[0].transaction.issued_at
        if continuum_time is not None:
            return format_date(continuum_time)
       
        return u"" 

    @property
    def updateuser(self):
        # Migrated versions may contain a updateuser attribute that must be used instead because
        # transaction.user is not set in the migration script. 
        legacy_username = self.attrs.get("updateuser")
        if legacy_username:
            return legacy_username

        continuum_user = self.transaction.user
        if continuum_user is not None:
            # XXX: not a really good idea but we keep that for backward compatibility
            return continuum_user.getName()
        # we don't know...
        return u""
            
    @property
    def creator(self):
        # Migrated versions may contain a creator attribute that must be used instead because
        # transaction.user is not set in the migration script. 
        legacy_username = self.attrs.get("creator")
        if legacy_username:
            return legacy_username

        continuum_user = self.versions[0].transaction.user
        if continuum_user is not None:
            # XXX: not a really good idea but we keep that for backward compatibility
            return continuum_user.getName()
        # we don't know...
        return u""
            