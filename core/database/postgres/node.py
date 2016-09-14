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
from sqlalchemy import (Table, Sequence, Integer, Unicode, Boolean, sql, text, select, func)
from sqlalchemy.orm import deferred, object_session
from sqlalchemy.orm.dynamic import AppenderQuery, AppenderMixin
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative.api import DeclarativeMeta
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.ext.hybrid import hybrid_property

from core import config
from core.node import NodeMixin, NodeVersionMixin
from core.database.postgres import db_metadata, DeclarativeBase, MtQuery, mediatumfunc, MtVersionBase, integer_fk
from core.database.postgres import rel, bref, C, FK
from core.database.postgres.alchemyext import LenMixin, view, exec_sqlfunc
from core.database.postgres.attributes import Attributes, AttributesExpressionAdapter
from ipaddr import IPv4Address, AddressValueError
from sqlalchemy_continuum import versioning_manager
from sqlalchemy_continuum.utils import version_class
from werkzeug.utils import cached_property
from core.search.representation import SearchTreeElement
from utils.date import format_date


logg = logging.getLogger(__name__)


USE_CACHED_CHILDCOUNT = config.getboolean("database.use_cached_childcount")


class NodeType(DeclarativeBase):

    """Node type / node class description.
    We don't need that in the application, that's just to inform Postgres about our types.
    """

    __tablename__ = "nodetype"

    name = C(Unicode, primary_key=True)
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
        if isinstance(field, basestring):
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


t_noderelation = Table("noderelation", db_metadata,
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
            .subquery())


def _subquery_subtree_distinct(node):
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

node_id_seq = Sequence('node_id_seq', schema=db_metadata.schema, start=100)

class Node(DeclarativeBase, NodeMixin):

    """Base class for Nodes which holds all SQLAlchemy fields definitions
    """
    __metaclass__ = BaseNodeMeta
    __tablename__ = "node"
    __versioned__ = {
        "base_classes": (NodeVersionMixin, MtVersionBase, DeclarativeBase),
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
    def a(self):
        """ see: Attributes"""
        if "_attributes_accessor" not in self.__dict__:
            setattr(self, "_attributes_accessor", Attributes(self, "attrs"))
        return self._attributes_accessor

    @a.expression
    def a_expr(self):
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
        sq = _subquery_subtree_distinct(self)
        return object_session(self).query(Content).filter(Node.id.in_(sq)).filter_by(subnode=False)

    @property
    def content_children_for_all_subcontainers_with_duplicates(self):
        """Collects all Content nodes in all subcontainers of this node.
        This excludes content nodes that are children of other content nodes.
        This method can be much faster than content_children_for_all_subcontainers, but may return lesser nodes than expected (when using limit).
        Don't use distinct() on this method, use content_children_for_all_subcontainers instead if you need it!
        """
        from contenttypes.data import Content
        nr = t_noderelation
        # TODO: check if it's better to use the _subquery_subtree() here
        return object_session(self).query(Content).filter_by(subnode=False).join(nr, Content.id == nr.c.cid).filter(nr.c.nid==self.id)

    @property
    def content_children_count_for_all_subcontainers(self):
        if USE_CACHED_CHILDCOUNT:
            return exec_sqlfunc(object_session(self), mediatumfunc.count_content_children_for_all_subcontainers(self.id))
        else:
            return self.content_children_for_all_subcontainers.count()


    def all_children_by_query(self, query):
        sq = _subquery_subtree_distinct(self)
        query = query.filter(Node.id.in_(sq))
        return query

    @staticmethod
    def req_has_access_to_node_id(node_id, accesstype, req=None, date=func.current_date()):
        # XXX: the database-independent code could move to core.node
        from core.transition import request
        from core.users import user_from_session

        if req is None:
            req = request

        user = user_from_session(req.session)

        # XXX: like in mysql version, what's the real solution?
        try:
            ip = IPv4Address(req.remote_addr)
        except AddressValueError:
            logg.warn("illegal IP address %s, refusing IP-based access", req.remote_addr)
            ip = None

        return Node.has_access_to_node_id(node_id, accesstype, user, ip, date)

    @staticmethod
    def has_access_to_node_id(node_id, accesstype, user=None, ip=None, date=None):
        # XXX: the database-independent code could move to core.node
        from core import db
        from core.users import get_guest_user

        if user is None:
            user = get_guest_user()

        if user.is_admin:
            return True

        if ip is None:
            ip = IPv4Address("0.0.0.0")

        if date is None:
            date = func.current_date()

        accessfunc = access_funcs[accesstype]
        group_ids = user.group_ids
        access = accessfunc(node_id, group_ids, ip, date)
        return db.session.execute(select([access])).scalar()

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

    def _search_query_object(self):
        """Builds the query object that is used as basis for content node searches below this node"""
        from contenttypes import Content
        q = object_session(self).query
        sq = _subquery_subtree(self)
        base_query = q(Content).filter(Node.id.in_(sq))
        return base_query

    def search(self, searchquery, languages=None):
        """Creates a search query.
        :param searchquery: query in search language or parsed query (search tree) as `SearchTreeElement`:
        :param language: sequence of language config strings matching Fts.config
        :returns: Node Query
        """
        from core.database.postgres.search import apply_searchtree_to_query
        searchtree = self._parse_searchquery(searchquery)
        query = self._search_query_object()
        return apply_searchtree_to_query(query, searchtree, languages)

    def search_multilang(self, searchquery, languages=None):
        """Creates search queries for a sequence of languages.
        :param searchquery: query in search language or parsed query (search tree) as `SearchTreeElement`:
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
                    tx.meta[u"tag"] = tag
                else:
                    NodeVersion = version_class(node.__class__)
                    # in case you were wondering: order_by(None) resets the default order_by
                    last_tagged_version = node.tagged_versions.order_by(None).order_by(NodeVersion.transaction_id.desc()).first()
                    if last_tagged_version is not None:
                        next_version = int(last_tagged_version.tag) + 1
                    else:
                        node.versions[-1].tag = u"1"
                        next_version = 2

                    tx.meta[u"tag"] = unicode(next_version)

                if comment:
                    tx.meta[u"comment"] = comment

                return tx

            def __exit__(self, exc_type, exc_value, traceback):
                if exc_type:
                    self.session.rollback()
                else:
                    self.session.commit()

        return VersionContextManager()

    def is_descendant_of(self, node):
        return exec_sqlfunc(object_session(self), mediatumfunc.is_descendant_of(self.id, node.id))

    def _get_nearest_ancestor_by_type(self, ancestor_type):
        """Returns a nearest ancestor of `ancestor_type`.
        If none is found, return `Collections` as default.
        It's undefined which one will be returned if more than one nearest ancestor is found.
        """
        nr = t_noderelation
        q = object_session(self).query

        maybe_ancestor = (q(ancestor_type)
                .join(nr, Node.id == nr.c.nid)
                .filter_by(cid=self.id)
                .order_by(nr.c.distance).limit(1).first())

        if maybe_ancestor is None:
            from contenttypes import Collections
            return q(Collections).one()

        return maybe_ancestor

    def get_container(self):
        from contenttypes import Container
        return self._get_nearest_ancestor_by_type(Container)

    def get_collection(self):
        from contenttypes import Collection
        return self._get_nearest_ancestor_by_type(Collection)

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
        return pyaml.dump(node_dict)


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


class NodeAlias(DeclarativeBase):

    """Alias name for a node that will be shown if the alias is requested in the frontend.
    A node can have multiple aliases."""

    __tablename__ = "node_alias"

    alias = C(Unicode, primary_key=True)
    nid = integer_fk(Node.id)
    description = C(Unicode)

    node = rel(Node)
