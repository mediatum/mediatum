# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
import datetime
import logging
from json import dumps
from warnings import warn

import pyaml
from sqlalchemy import (Table, Sequence, Integer, Unicode, Text, Boolean, sql, text, select, func)
from sqlalchemy.orm import deferred, object_session
from sqlalchemy.orm.dynamic import AppenderQuery, AppenderMixin
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative.api import DeclarativeMeta
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.ext.hybrid import hybrid_property

from core.node import NodeMixin, NodeVersionMixin
from core.database.postgres import db_metadata, DeclarativeBase, MtQuery, mediatumfunc, MtVersionBase
from core.database.postgres import rel, bref, C, FK
from core.database.postgres.alchemyext import LenMixin, view, exec_sqlfunc
from core.database.postgres.attributes import Attributes, AttributesExpressionAdapter
from utils.magicobjects import MInt
from ipaddr import IPv4Address
from sqlalchemy_continuum import versioning_manager
from sqlalchemy_continuum.utils import version_class


logg = logging.getLogger(__name__)


class NodeType(DeclarativeBase):

    """Node type / node class description.
    We don't need that in the application, that's just to inform Postgres about our types.
    """

    __tablename__ = "nodetype"

    name = C(Text, primary_key=True)
    # does this type act as a container type? Other types are "content types".
    is_container = C(Boolean, index=True)


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
        if isinstance(field, str):
            # handle some special cases
            if field == "name" or field == "nodename":
                warn("use query.order_by(Node.name) instead", DeprecationWarning)
                return self.sort_by_name("up")
            elif field == "-name" or field == "nodename":
                warn("use query.order_by(Node.name.desc()) instead", DeprecationWarning)
                return self.sort_by_name("down")
            elif field in ("orderpos", "-orderpos"):
                raise NotImplementedError("this method must not be used for orderpos sorting, use query.order_by(Node.orderpos)!")
            else:
                warn("use query.order_by(Node.attrs[field]).order_by ... instead", DeprecationWarning)
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


t_noderelation = Table("noderelation", db_metadata,
                       C("nid", Integer, FK("node.id"), primary_key=True, index=True),
                       C("cid", Integer, FK("node.id", ondelete="CASCADE"), primary_key=True, index=True),
                       C("distance", Integer, primary_key=True, index=True))


class BaseNodeMeta(DeclarativeMeta):

    def __init__(cls, name, bases, dct):  # @NoSelf
        """Add mapper args with a default polymorphic_identity
        of classname in lowercase if not defined.
        """
        args = dict(polymorphic_identity=cls.__name__.lower())
        if "__mapper_args__" not in cls.__dict__:
            logg.debug("poly identity %s", args)
            cls.__mapper_args__ = args
        super(BaseNodeMeta, cls).__init__(name, bases, dct)


def _cte_subtree(node):
    from core import db

    query = db.query(t_noderelation.c.cid).\
        filter(t_noderelation.c.nid == node.id).\
        distinct().\
        cte(name="subtree")

    return query


def _subquery_subtree(node):
    from core import db

    return (db.query(t_noderelation.c.cid)
            .filter(t_noderelation.c.nid == node.id)
            .distinct()
            .subquery())


def _subquery_subtree_container(node):
    from contenttypes.container import Container
    from core import db

    query = (db.query(t_noderelation.c.cid)
             .filter(t_noderelation.c.nid == node.id)
             .join(Container, Container.id == t_noderelation.c.cid)
             .subquery())

    return query


# permission check functions for the access types
access_funcs = {
    "read": mediatumfunc.has_read_access_to_node,
    "write": mediatumfunc.has_write_access_to_node,
    "data": mediatumfunc.has_data_access_to_node
}


class Node(DeclarativeBase, NodeMixin):

    """Base class for Nodes which holds all SQLAlchemy fields definitions
    """
    __metaclass__ = BaseNodeMeta
    __tablename__ = "node"
    __versioned__ = {
        "base_classes": (NodeVersionMixin, MtVersionBase, DeclarativeBase),
        "exclude": ["subnode"]
    }

    id = C(Integer, Sequence('node_id_seq', schema=db_metadata.schema, start=100), primary_key=True)
    type = C(Text, index=True)
    schema = C(Unicode, index=True)
    name = C(Unicode, index=True)
    orderpos = C(Integer, default=1, index=True)
    fulltext = deferred(C(Text))
    # indicate that this node is a subnode of a content type node
    # subnode exists just for performance reasons and is updated by the database
    subnode = C(Boolean, server_default="false")

    attrs = deferred(C(MutableDict.as_mutable(JSONB)))

    @hybrid_property
    def a(self):
        """ see: Attributes"""
        if "_attributes_accessor" not in self.__dict__:
            setattr(self, "_attributes_accessor", Attributes(self))
        return self._attributes_accessor

    @a.expression
    def a_expr(self):
        """ see: AttributesExpression"""
        if "_attributes_accessor" not in self.__dict__:
            setattr(self, "_attributes_accessor", AttributesExpressionAdapter(self))
        return self._attributes_accessor

    @a.setter
    def a_set(self, value):
        raise NotImplementedError("immutable!")

    def __init__(self, name="", type="node", id=None, schema=None, attrs=None, orderpos=None):
        self.name = name
        if "/" in type:
            warn("use separate type and schema parameters instead of 'type/schema'", DeprecationWarning)
            type, schema = type.split("/")
        self.type = type
        self.attrs = MutableDict()
        if id:
            self.id = id
        if schema:
            self.schema = schema
        if attrs:
            self.attrs.update(attrs)
        if orderpos:
            self.orderpos = orderpos

    @property
    def slow_content_children_for_all_subcontainers(self):
        """
        !!! very slow, use content_children_for_all_subcontainers instead!!!
        Collects all Content nodes in all subcontainers of this node.
        This excludes content nodes that are children of other content nodes.
        """
        warn("very slow, use content_children_for_all_subcontainers instead", DeprecationWarning)
        from contenttypes.data import Content
        from core import db
        sq = _subquery_subtree_container(self)
        query = db.query(Content).\
            join(t_noderelation, Node.id == t_noderelation.c.cid).\
            filter(t_noderelation.c.nid.in_(sq) | (t_noderelation.c.nid == self.id)).\
            filter(t_noderelation.c.distance == 1)

        return query

    @property
    def content_children_for_all_subcontainers(self):
        """Collects all Content nodes in all subcontainers of this node.
        This excludes content nodes that are children of other content nodes.
        """
        from contenttypes.data import Content
        from core import db
        sq = _subquery_subtree(self)
        return object_session(self).query(Content).filter(Node.id.in_(sq)).filter_by(subnode=False)

    def all_children_by_query(self, query):
        sq = _subquery_subtree(self)
        query = query.filter(Node.id.in_(sq))
        return query

    @staticmethod
    def req_has_access_to_node_id(node_id, accesstype, req=None, date=func.current_date()):
        from core.transition import request
        from core.users import user_from_session

        if req is None:
            req = request

        user = user_from_session(req.session)

        ip = IPv4Address(req.remote_addr)
        return Node.has_access_to_node_id(node_id, accesstype, user, ip, date)

    @staticmethod
    def has_access_to_node_id(node_id, accesstype, user=None, ip=None, date=func.current_date()):
        from core import db

        if user.is_admin:
            return True

        accessfunc = access_funcs[accesstype]
        group_ids = user.group_ids if user else None
        access = accessfunc(node_id, group_ids, ip, date)
        return db.session.execute(select([access])).scalar()

    def _parse_searchquery(self, searchquery):
        """Parses `searchquery` and transforms it into the search tree."""
        from core.search import parser
        q = object_session(self).query
        searchtree = parser.parse_string(searchquery)
        return searchtree

    def _search_query_object(self):
        """Builds the query object that is used as basis for content node searches below this node"""
        from contenttypes import Content
        q = object_session(self).query
        base_query = self.all_children_by_query(q(Content))
        return base_query

    def search(self, searchquery, languages=None):
        """Creates a search query.
        :param searchquery: query in search language
        :param language: sequence of language config strings matching Fts.config
        :returns: Node Query
        """
        from core.database.postgres.search import apply_searchtree_to_query
        searchtree = self._parse_searchquery(searchquery)
        query = self._search_query_object()
        return apply_searchtree_to_query(query, searchtree, languages)

    def search_multilang(self, searchquery, languages=None):
        """Creates search queries for a sequence of languages.
        :param searchquery: query in search language :
        :param languages: language config strings matching Fts.config
        :returns list of Node Query
        """
        from core.database.postgres.search import apply_searchtree_to_query
        searchtree = self._parse_searchquery(searchquery)
        query = self._search_query_object()
        return [apply_searchtree_to_query(query, searchtree, l) for l in languages]

    @property
    def tagged_versions(self):
        Transaction = versioning_manager.transaction_cls
        TransactionMeta = versioning_manager.transaction_meta_cls
        version_cls = version_class(self.__class__)
        return (self.versions.join(Transaction, version_cls.transaction_id == Transaction.id).join(Transaction.meta_relation).
                filter(TransactionMeta.key == u"tag"))

    def get_tagged_version(self, tag):
        return self.tagged_versions.filter_by(value=tag).scalar()

    def new_tagged_version(self, tag=None, comment=None, user=None):
        """Returns a context manager that manages the creation of a new tagged node version.

        :param tag: a unicode tag assigned to the transaction belonging to the new version.
            If none is given, assume that we want to add a new numbered version.
            The tag will be the incremented version number of the last numbered version.
            If no numbered version is present, assign 1 to the last version and 2 to the new version.

        :param comment: optional comment for the transaction
        :param user: user that will be associated with the transaction.
        """
        node = self

        class VersionContextManager(object):

            def __enter__(self):
                self.session = s = object_session(node)
                if s.new or s.dirty:
                    raise Exception("Refusing to create a new tagged node version. Session must be clean!")

                uow = versioning_manager.unit_of_work(s)
                tx = uow.create_transaction(s)

                if user is not None:
                    tx.user = user

                if tag:
                    tx.meta["tag"] = tag
                else:
                    NodeVersion = version_class(node.__class__)
                    # in case you were wondering: order_by(None) resets the default order_by
                    last_tagged_version = node.tagged_versions.order_by(None).order_by(NodeVersion.transaction_id.desc()).first()
                    if last_tagged_version is not None:
                        next_version = int(last_tagged_version.tag) + 1
                    else:
                        node.versions[-1].tag = u"1"
                        next_version = 2

                    tx.meta["tag"] = unicode(next_version)

                if comment:
                    tx.meta["comment"] = comment

                # XXX: Actually, we could use the transaction time instead of writing an update time.
                # But this is the old way, keep it because the application expects it.
                node["updatetime"] = datetime.datetime.now().isoformat()
                return tx

            def __exit__(self, exc_type, exc_value, traceback):
                if exc_type:
                    self.session.rollback()
                else:
                    self.session.commit()

        return VersionContextManager()

    def is_descendant_of(self, node):
        return exec_sqlfunc(object_session(self), mediatumfunc.is_descendant_of(self.id, node.id))

    __mapper_args__ = {
        'polymorphic_identity': 'node',
        'polymorphic_on': type
    }

    def to_yaml(self):
        """overwrite default DeclarativeBase.to_yaml method because we need to convert MutableDict and MInt first
        """
        as_dict = self.to_dict()
        as_dict["attrs"] = dict(as_dict["attrs"])
        as_dict["id"] = str(as_dict["id"])
        return pyaml.dump(as_dict)


# view for direct parent-child relationship (distance = 1), also used for inserting new node connections
t_nodemapping = view("nodemapping", db_metadata,
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
    query_class=NodeAppenderQuery
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

# define Node child/parent relationships here

Node.children = children_rel(Node, backref=bref("parents", lazy="dynamic", query_class=NodeAppenderQuery))
Node.all_children = all_children_rel(Node)
