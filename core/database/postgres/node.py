# -*- coding: utf-8 -*-

# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import contextlib as _contextlib
import itertools as _itertools
import logging
from warnings import warn

import ruamel.yaml as _ruamel_yaml
import sqlalchemy as _sqlalchemy
import sqlalchemy_continuum as _sqlalchemy_continuum
import sqlalchemy_continuum.plugins.flask as _
import sqlalchemy_continuum.plugins.transaction_meta as _
import sqlalchemy.orm as _
from sqlalchemy import (Table, Sequence, Integer, Unicode, Boolean, sql, text, select, func)
from sqlalchemy.orm import deferred, object_session
from sqlalchemy.orm.dynamic import AppenderMixin
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative.api import DeclarativeMeta
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.ext.hybrid import hybrid_property

import flask as _flask

import core as _core
import core.database.postgres as _
from core.node import NodeMixin, NodeVersionMixin
from core.database.postgres import rel, bref, C, FK
from core.database.postgres.alchemyext import LenMixin, view, exec_sqlfunc
from core.database.postgres.attributes import Attributes, AttributesExpressionAdapter
from ipaddr import IPv4Address, AddressValueError
from sqlalchemy_continuum import versioning_manager
from sqlalchemy_continuum.utils import version_class
from core.search.representation import SearchTreeElement


logg = logging.getLogger(__name__)

_sqlalchemy_continuum.make_versioned(
        plugins=[
                _sqlalchemy_continuum.plugins.transaction_meta.TransactionMetaPlugin(),
                _sqlalchemy_continuum.plugins.flask.FlaskPlugin()
            ],
        options=dict(
            native_versioning=True,
            base_classes= (
                _core.database.postgres.continuumext.MtVersionBase,
                _core.database.postgres.DeclarativeBase,
            ),
        )
    )


class NodeType(_core.database.postgres.DeclarativeBase):

    """Node type / node class description.
    We don't need that in the application, that's just to inform Postgres about our types.
    """

    __tablename__ = "nodetype"

    name = C(Unicode, primary_key=True)
    # does this type act as a container type? Other types are "content types".
    is_container = C(Boolean, index=True)


class MtQuery(_sqlalchemy.orm.Query):

    def node_offset0(self):
        # offset0 is used to prevent the postgresql planner from using other (slower) scan
        # methods than a Bitmap Index Scan
        query = self.options(_sqlalchemy.orm.undefer("*")).offset(0).from_self()
        deferred_columns = (prop.key for prop in _sqlalchemy.orm.class_mapper(Node).iterate_properties
                            if isinstance(prop, _sqlalchemy.orm.ColumnProperty) and prop.deferred)
        return query.options(*_itertools.imap(_sqlalchemy.orm.defer, deferred_columns))

    def prefetch_attrs(self):
        return self.options(_sqlalchemy.orm.undefer(Node.attrs))

    def prefetch_system_attrs(self):
        return self.options(_sqlalchemy.orm.undefer(Node.system_attrs))

    def _find_nodeclass(self):
        """Returns the query's underlying model classes."""
        nodeclass = dict()  # stores node class in key 0
        for d in self.column_descriptions:
            d = d["entity"]
            if issubclass(d, Node):
                # class found: memorize it, but fail if it's not unique
                if nodeclass.setdefault(0, d) is not d:
                    raise AssertionError("Non-unique node class")
        return nodeclass.get(0)

    def filter_read_access(self, user=None, ip=None, req=None):
        return self._filter_access("read", user, ip, req)

    def filter_write_access(self, user=None, ip=None, req=None):
        return self._filter_access("write", user, ip, req)

    def filter_data_access(self, user=None, ip=None, req=None):
        return self._filter_access("data", user, ip, req)

    def _filter_access(self, accesstype, user=None, ip=None, req=None):
        group_ids, ip, date = _core.database.postgres.build_accessfunc_arguments(user, ip, req=req)

        if group_ids is None and ip is None and date is None:
            # everything is None means: permission checks always pass, so we can skip access checks completely.
            # This will happen for an admin user.
            return self

        nodeclass = self._find_nodeclass()
        if not nodeclass:
            return self

        db_funcs = {
            "read": _core.database.postgres.mediatumfunc.has_read_access_to_node,
            "write": _core.database.postgres.mediatumfunc.has_write_access_to_node,
            "data": _core.database.postgres.mediatumfunc.has_data_access_to_node
        }

        try:
            db_accessfunc = db_funcs[accesstype]
        except KeyError:
            raise ValueError(
                "accesstype '{}' does not exist, accesstype must be one of: read, write, data".format(accesstype))

        access_filter = db_accessfunc(nodeclass.id, group_ids, ip, date)
        return self.filter(access_filter)

    def get(self, ident):
        nodeclass = self._find_nodeclass()
        if not nodeclass:
            return _sqlalchemy.orm.Query.get(self, ident)
        active_version = _sqlalchemy.orm.Query.get(self, ident)
        Transaction = versioning_manager.transaction_cls
        if active_version is None:
            ver_cls = version_class(nodeclass)
            return (self.session.query(ver_cls).join(Transaction, ver_cls.transaction_id == Transaction.id)
                    .join(Transaction.meta_relation)
                    .filter_by(key=u'alias_id', value=unicode(ident)).scalar())

        return active_version


class NodeAppenderQuery(AppenderMixin, LenMixin, MtQuery):

    """Custom AppenderQuery class with additional methods for node handling
    """

    def sort_by_orderpos(self, reverse=False):
        if reverse:
            warn("use .order_by(Node.orderpos.desc()) instead", DeprecationWarning)
            return self.order_by(Node.orderpos.desc())
        else:
            warn("use .order_by(Node.orderpos) instead", DeprecationWarning)
            return self.order_by(Node.orderpos)

    def sort_by_name(self, direction="up"):
        reverse = direction != "up"
        if reverse:
            warn("use .order_by(Node.name.desc()) instead", DeprecationWarning)
            return self.order_by(Node.name.desc())
        else:
            warn("use .order_by(Node.name) instead", DeprecationWarning)
            return self.order_by(Node.name)

    def getIDs(self):
        warn("inefficient, rewrite your code using SQLA queries", DeprecationWarning)
        return [n.id for n in self.all()]

    def sort_by_fields(self, field):
        if isinstance(field, basestring):
            # handle some special cases
            if field == "name" or field == "nodename":
                warn("use query.order_by(Node.name) instead", DeprecationWarning)
                return self.sort_by_name("up")
            elif field == "-name" or field == "-nodename":
                warn("use query.order_by(Node.name.desc()) instead", DeprecationWarning)
                return self.sort_by_name("down")
            elif field in ("orderpos", "-orderpos"):
                raise NotImplementedError("this method must not be used for orderpos sorting, use query.order_by(Node.orderpos)!")
            else:
                warn("use query.order_by(Node.attrs[field]) instead", DeprecationWarning)
                fields = [field]
        else:
            # remove empty sortfields
            fields = [f for f in field if f]
            if not fields:
                # no fields left, all empty...
                return self
        query = self
        for field in fields:
            if field.startswith("-"):
                expr = Node.attrs[field[1:]].astext.desc()
            else:
                expr = Node.attrs[field].astext
            query = query.order_by(expr)

        return query


t_noderelation = Table("noderelation", _core.database.postgres.db_metadata,
                       C("nid", Integer, FK("node.id"), primary_key=True, index=True),
                       C("cid", Integer, FK("node.id", ondelete="CASCADE"), primary_key=True, index=True),
                       # SQLAlchemy automatically generates primary key integers as SERIAL.
                       # We don't want that for the distance, disable with autoincrement=False
                       C("distance", Integer, primary_key=True, autoincrement=False, index=True))


class BaseNodeMeta(DeclarativeMeta):

    def __init__(cls, name, bases, dct):  # @NoSelf
        """Add mapper args with a default polymorphic_identity
        of classname in lowercase if not defined.
        """
        args = dict(polymorphic_identity=unicode(cls.__name__.lower()))
        if "__mapper_args__" not in cls.__dict__:
            logg.debug("poly identity %s", args)
            cls.__mapper_args__ = args
        super(BaseNodeMeta, cls).__init__(name, bases, dct)


def _cte_subtree(node):

    query = _core.db.query(t_noderelation.c.cid).\
        filter(t_noderelation.c.nid == node.id).\
        distinct().\
        cte(name="subtree")

    return query


def subquery_subtree_distinct(node):

    return (_core.db.query(t_noderelation.c.cid)
            .filter(t_noderelation.c.nid == node.id)
            .distinct()
            .subquery())


# permission check functions for the access types
access_funcs = {
    "read": _core.database.postgres.mediatumfunc.has_read_access_to_node,
    "write": _core.database.postgres.mediatumfunc.has_write_access_to_node,
    "data": _core.database.postgres.mediatumfunc.has_data_access_to_node
}

node_id_seq = Sequence('node_id_seq', schema=_core.database.postgres.db_metadata.schema, start=100)

class Node(_core.database.postgres.DeclarativeBase, NodeMixin):

    """Base class for Nodes which holds all SQLAlchemy fields definitions
    """
    __metaclass__ = BaseNodeMeta
    __tablename__ = "node"
    __versioned__ = {
        "base_classes": (
            NodeVersionMixin,
            _core.database.postgres.MtVersionBase,
            _core.database.postgres.DeclarativeBase,
            ),
        "exclude": ["subnode", "system_attrs"]
    }

    id = C(Integer, node_id_seq, server_default=node_id_seq.next_value(), primary_key=True)
    type = C(Unicode, index=True)
    schema = C(Unicode, index=True)
    name = C(Unicode, index=True)
    orderpos = C(Integer, default=1, index=True)
    fulltext = deferred(C(Unicode))
    # indicate that this node is a subnode of a content type node
    # subnode exists just for performance reasons and is updated by the database
    # unversioned
    subnode = C(Boolean, server_default="false")

    attrs = deferred(C(MutableDict.as_mutable(JSONB)))
    # Migration from old mediatum: all attributes starting with "system." go here.
    # We should get rid of most (all?) such attributes in the future.
    # unversioned
    system_attrs = deferred(C(MutableDict.as_mutable(JSONB)))

    @hybrid_property
    def a_expr(self):
        """ see: Attributes"""
        raise Exception("node.a_expr")
        if "_attributes_accessor" not in self.__dict__:
            setattr(self, "_attributes_accessor", Attributes(self, "attrs"))
        return self._attributes_accessor

    @a_expr.expression
    def a(self):
        """ see: AttributesExpression"""
        if "_attributes_accessor" not in self.__dict__:
            setattr(self, "_attributes_accessor", AttributesExpressionAdapter(self, "attrs"))
        return self._attributes_accessor

    @a.setter
    def a_set(self, value):
        raise NotImplementedError("immutable!")


    @hybrid_property
    def sys(self):
        """ see: Attributes"""
        if "_system_attributes_accessor" not in self.__dict__:
            setattr(self, "_system_attributes_accessor", Attributes(self, "system_attrs"))
        return self._system_attributes_accessor

    @sys.expression
    def sys_expr(self):
        """ see: AttributesExpression"""
        if "_system_attributes_accessor" not in self.__dict__:
            setattr(self, "_system_attributes_accessor", AttributesExpressionAdapter(self, "system_attrs"))
        return self._system_attributes_accessor

    @a.setter
    def sys_set(self, value):
        raise NotImplementedError("immutable!")


    def __init__(self, name=u"", type=u"node", id=None, schema=None, attrs=None, system_attrs=None, orderpos=None):
        self.name = name
        if not isinstance(type, unicode):
            warn("type arg of Node should be unicode (hint: don't create nodes with Node(type='{}')!)".format(type), DeprecationWarning)

        if "/" in type:
            warn("use separate type and schema parameters instead of 'type/schema'", DeprecationWarning)
            type, schema = type.split("/")

        self.type = type
        self.attrs = MutableDict()
        self.system_attrs = MutableDict()
        if id:
            self.id = id
        if schema:
            self.schema = schema
        if attrs:
            self.attrs.update(attrs)
        if system_attrs:
            self.system_attrs.update(system_attrs)
        if orderpos:
            self.orderpos = orderpos

    def all_children_by_query(self, query):
        sq = subquery_subtree_distinct(self)
        query = query.filter(Node.id.in_(sq))
        return query

    @staticmethod
    def req_has_access_to_node_id(node_id, accesstype, req=None, date=func.current_date()):
        # XXX: the database-independent code could move to core.node
        from core.users import user_from_session

        if req is None:
            req = _flask.request

        user = user_from_session()

        # XXX: like in mysql version, what's the real solution?
        try:
            ip = IPv4Address(req.remote_addr)
        except AddressValueError:
            logg.warning("illegal IP address %s, refusing IP-based access", req.remote_addr)
            ip = None

        return _core.users.has_access_to_node_id(node_id, accesstype, user, ip, date)

    def _parse_searchquery(self, searchquery):
        """
        * `searchquery` is a string type: Parses `searchquery` and transforms it into the search tree.
        * `searchquery` already is already in search tree form: work is already done, return it unchanged.
        """
        from core.search import parse_searchquery
        if isinstance(searchquery, SearchTreeElement):
            searchtree = searchquery
        else:
            searchtree = parse_searchquery(searchquery)
        return searchtree

    @property
    def tagged_versions(self):
        Transaction = versioning_manager.transaction_cls
        TransactionMeta = versioning_manager.transaction_meta_cls
        version_cls = version_class(self.__class__)
        return (self.versions.join(Transaction, version_cls.transaction_id == Transaction.id).join(Transaction.meta_relation).
                filter(TransactionMeta.key == u"tag"))

    def get_tagged_version(self, tag):
        return self.tagged_versions.filter_by(value=tag).scalar()

    def get_published_version(self):
        Transaction = versioning_manager.transaction_cls
        TransactionMeta = versioning_manager.transaction_meta_cls
        version_cls = version_class(self.__class__)
        published_versions = self.versions.join(Transaction, version_cls.transaction_id == Transaction.id).\
                join(Transaction.meta_relation). filter(TransactionMeta.key == u"publish")
        return published_versions.scalar()

    @_contextlib.contextmanager
    def new_tagged_version(self, tag=None, comment=None, publish=None, user=None):
        """Returns a context manager that manages the creation of a new tagged node version.

        :param tag: a unicode tag assigned to the transaction belonging to the new version.
            If none is given, assume that we want to add a new numbered version.
            The tag will be the incremented version number of the last numbered version.
            If no numbered version is present, assign 1 to the last version and 2 to the new version.

        :param comment: optional comment for the transaction
        :param user: user that will be associated with the transaction.
        """
        node = self

        self.session = s = object_session(node)
        if s.new or s.dirty:
            raise Exception("Refusing to create a new tagged node version. Session must be clean!")

        uow = versioning_manager.unit_of_work(s)
        tx = uow.create_transaction(s)

        if user is not None:
            tx.user = user

        if tag:
            if node.get_tagged_version(tag):
                raise ValueError("tag already exists")
            tx.meta[u"tag"] = tag
        elif publish:
            if node.get_published_version():
                raise ValueError("publish version already exists")
            tx.meta[u"publish"] = publish
        else:
            NodeVersion = version_class(node.__class__)
            # in case you were wondering: order_by(None) resets the default order_by
            last_tagged_version = node.tagged_versions.order_by(None).order_by(NodeVersion.transaction_id.desc()).first()
            if last_tagged_version is not None:
                next_version = int(last_tagged_version.tag) + 1
            else:
                next_version = 1

            tx.meta[u"tag"] = unicode(next_version)

        if comment:
            tx.meta[u"comment"] = comment

        try:
            yield
        except:
            self.session.rollback()
            raise
        self.session.commit()

    def is_descendant_of(self, node):
        return exec_sqlfunc(object_session(self), _core.database.postgres.mediatumfunc.is_descendant_of(self.id, node.id))

    def get_self_or_first_ancestor(self, typ):
        """Returns a nearest ancestor of `ancestor_type`.
        If none is found, return `Collections` as default.
        It's undefined which one will be returned if more than one nearest ancestor is found.
        """
        if isinstance(self, typ):
            return self

        return (object_session(self)
                .query(typ)
                .join(t_noderelation, Node.id == t_noderelation.c.nid)
                .filter_by(cid=self.id)
                .order_by(t_noderelation.c.distance)
                .limit(1)
                .first()
                )

    def get_parent_sortfield(self):
        """Returns a nearest ancestor with non-empty sortfield.
        """
        first_ancestor_with_sortfield = self.all_parents.filter(Node.a.sortfield != u'').order_by('distance').first()
        return first_ancestor_with_sortfield

    @property
    def has_files(self):
        return len(self.file_objects) > 0

    __mapper_args__ = {
        'polymorphic_identity': 'node',
        'polymorphic_on': type
    }

    def to_yaml(self):
        """overwrite default DeclarativeBase.to_yaml method because we need to convert MutableDicts first
        """
        node_dict = self.to_dict()
        node_dict["attrs"] = dict(node_dict["attrs"])
        node_dict["system_attrs"] = dict(node_dict["system_attrs"])
        return _ruamel_yaml.round_trip_dump(node_dict)

    def get_editor_menu(self, user, multiple_nodes, has_child):
        return ("metadata", {"menuoperation": ("acls", "admin",)},)


# view for direct parent-child relationship (distance = 1), also used for inserting new node connections
t_nodemapping = view("nodemapping", _core.database.postgres.db_metadata,
                     sql.select([t_noderelation.c.nid, t_noderelation.c.cid]).where(t_noderelation.c.distance == text("1")))

# helpers for node child/parent relationships

_children_rel_options = dict(
    secondary=t_nodemapping,
    lazy="dynamic",
    primaryjoin=Node.id == t_nodemapping.c.nid,
    secondaryjoin=Node.id == t_nodemapping.c.cid,
    query_class=NodeAppenderQuery
)

_all_children_rel_options = dict(
    secondary=t_noderelation,
    lazy="dynamic",
    primaryjoin=Node.id == t_noderelation.c.nid,
    secondaryjoin=Node.id == t_noderelation.c.cid,
    query_class=NodeAppenderQuery,
    viewonly=True
)

_parents_rel_options = dict(
    secondary=t_nodemapping,
    lazy="dynamic",
    primaryjoin=Node.id == t_nodemapping.c.cid,
    secondaryjoin=Node.id == t_nodemapping.c.nid,
    query_class=NodeAppenderQuery,
    viewonly=True
)

_all_parents_rel_options = dict(
    secondary=t_noderelation,
    lazy="dynamic",
    primaryjoin=Node.id == t_noderelation.c.cid,
    secondaryjoin=Node.id == t_noderelation.c.nid,
    query_class=NodeAppenderQuery,
    viewonly=True
)


def children_rel(*args, **kwargs):
    extended_kwargs = _children_rel_options.copy()
    extended_kwargs.update(kwargs)
    return rel(*args, **extended_kwargs)


def all_children_rel(*args, **kwargs):
    extended_kwargs = _all_children_rel_options.copy()
    extended_kwargs.update(kwargs)
    return rel(*args, **extended_kwargs)


def parents_rel(*args, **kwargs):
    extended_kwargs = _parents_rel_options.copy()
    extended_kwargs.update(kwargs)
    return rel(*args, **extended_kwargs)


def all_parents_rel(*args, **kwargs):
    extended_kwargs = _all_parents_rel_options.copy()
    extended_kwargs.update(kwargs)
    return rel(*args, **extended_kwargs)

# define Node child/parent relationships here

Node.children = children_rel(Node, backref=bref("parents", lazy="dynamic", query_class=NodeAppenderQuery))
Node.all_children = all_children_rel(Node)
Node.all_parents = all_parents_rel(Node)
