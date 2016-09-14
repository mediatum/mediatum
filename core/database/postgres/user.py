# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from itertools import chain
import logging

from sqlalchemy import Unicode, UnicodeText, Boolean, Table, DateTime, UniqueConstraint, String
from sqlalchemy.dialects.postgresql import ARRAY, ExcludeConstraint
from sqlalchemy.orm.session import object_session
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy_utils.types import EmailType

from core.database.postgres import DeclarativeBase, db_metadata
from core.database.postgres import rel, C, FK, bref
from core.database.postgres import TimeStamp, integer_fk, integer_pk
from core import config
from core.user import UserMixin
from core.usergroup import UserGroupMixin
from core import db
from core.database.postgres.permission import NodeToAccessRuleset

q = db.query


logg = logging.getLogger(__name__)


class AuthenticatorInfo(DeclarativeBase):

    __tablename__ = "authenticator"

    id = integer_pk()
    name = C(Unicode, nullable=False)
    auth_type = C(Unicode, nullable=False)

    @property
    def authenticator_key(self):
        return (self.auth_type, self.name)

    def __unicode__(self):
        return self.auth_type + ":" + self.name

    def __repr__(self):
        return u"AuthenticatorInfo<id: {} key: ({}, {})> ({})".format(self.id, self.name,
                                                                      self.auth_type, object.__repr__(self)).encode("utf8")

    __table_args__ = (UniqueConstraint(name, auth_type),)


class UserGroup(DeclarativeBase, TimeStamp, UserGroupMixin):

    __tablename__ = "usergroup"
    __versioned__ = {}

    id = integer_pk()
    name = C(Unicode, nullable=False, unique=True)
    description = C(UnicodeText)
    hidden_edit_functions = C(ARRAY(Unicode), server_default="{}")

    is_editor_group = C(Boolean, server_default="false")
    is_workflow_editor_group = C(Boolean, server_default="false")
    is_admin_group = C(Boolean, server_default="false")

    users = association_proxy("user_assocs", "user", creator=lambda u: UserToUserGroup(user=u))

    @property
    def user_names(self):
        _user_names = [unicode(u) for u in self.users]
        return sorted(_user_names, key=unicode.lower)

    @property
    def metadatatype_access(self):
        from schema.schema import Metadatatype
        return db.query(Metadatatype).join(NodeToAccessRuleset).filter_by(ruleset_name=self.name).all()

    def __unicode__(self):
        return self.name

    def __repr__(self):
        return u"UserGroup<{} '{}'> ({})".format(self.id, self.name, object.__repr__(self)).encode("utf8")


def create_special_user_dirs():
    from contenttypes import Directory
    return [Directory(u"upload", system_attrs={u"used_as": u"upload"}),
            Directory(u"trash", system_attrs={u"used_as": u"trash"})]


class User(DeclarativeBase, TimeStamp, UserMixin):

    __tablename__ = "user"
    __versioned__ = {}

    id = integer_pk()
    login_name = C(Unicode, nullable=False)
    display_name = C(Unicode)

    lastname = C(Unicode)
    firstname = C(Unicode)
    telephone = C(Unicode)
    organisation = C(Unicode)
    comment = C(UnicodeText)
    email = C(EmailType)
    password_hash = C(String)
    salt = C(String)
    password = u''

    # user activity
    last_login = C(DateTime)
    active = C(Boolean, server_default="true")

    # options
    can_edit_shoppingbag = C(Boolean, server_default="false")
    can_change_password = C(Boolean, server_default="false")

    home_dir_id = integer_fk("node.id")

    # relationships
    groups = association_proxy("group_assocs", "usergroup", creator=lambda ug: UserToUserGroup(usergroup=ug))
    home_dir = rel("Directory", foreign_keys=[home_dir_id])

    authenticator_info = rel(AuthenticatorInfo)
    authenticator_id = integer_fk(AuthenticatorInfo.id, nullable=False)

    @property
    def group_ids(self):
        return [g.id for g in self.groups]

    @property
    def group_names(self):
        return [g.name for g in self.groups]

    @property
    def is_editor(self):
        return any(g.is_editor_group for g in self.groups)

    @property
    def is_admin(self):
        return any(g.is_admin_group for g in self.groups)

    @property
    def is_guest(self):
        return self.login_name == config.get_guest_name() and self.authenticator_id == 0
    
    @property
    def is_workflow_editor(self):
        return any(g.is_workflow_editor_group for g in self.groups)

    @property
    def hidden_edit_functions(self):
        return [f for group in self.groups for f in group.hidden_edit_functions or []]

    @property
    def upload_dir(self):
        from contenttypes import Directory
        if self.home_dir:
            return self.home_dir.children.filter(Directory.system_attrs[u"used_as"].astext == u"upload").one()

    @property
    def trash_dir(self):
        from contenttypes import Directory
        if self.home_dir:
            return self.home_dir.children.filter(Directory.system_attrs[u"used_as"].astext == u"trash").one()

    def get_or_add_private_group(self):
        """Gets the private group for this user.
        Creates the group if it's missing and adds it to the session.
        Always use this method and don't create private groups by yourself!
        :rtype: UserGroup
        """

        maybe_group_assoc = [g for g in self.group_assocs if g.private == True]

        if not maybe_group_assoc:
            # the name doesn't really matter, but it must be unique
            group = UserGroup(name=u"_user_{}".format(unicode(self.id)))
            group_assoc = UserToUserGroup(usergroup=group, private=True)
            self.group_assocs.append(group_assoc)
        else:
            group = maybe_group_assoc[0].usergroup

        return group

    def change_password(self, password):
        from core.auth import create_password_hash
        self.password_hash, self.salt = create_password_hash(password)

    def create_home_dir(self):
        from contenttypes.container import Directory, Home
        from core.database.postgres.permission import AccessRulesetToRule
        from core.permission import get_or_add_access_rule
        s = object_session(self)
        home_root = s.query(Home).one()
        homedir_name = self.login_name
        home = Directory(homedir_name)
        home_root.container_children.append(home)
        home.children.extend(create_special_user_dirs())
        # add access rules so only the user itself can access the home dir
        private_group = self.get_or_add_private_group()
        # we need the private group ID, it's set on flush by the DB
        s.flush()
        user_access_rule = get_or_add_access_rule(group_ids=[private_group.id])

        for access_type in (u"read", u"write", u"data"):
            ruleset = home.get_or_add_special_access_ruleset(access_type)
            arr = AccessRulesetToRule(rule=user_access_rule)
            ruleset.rule_assocs.append(arr)

        self.home_dir = home
        logg.info("created home dir for user '%s (id: %s)'", self.login_name, self.id)
        return home

    # Flask-Login integration functions
    def is_authenticated(self):
        return not self.is_guest

    def is_active(self):
        return not self.is_guest

    @property
    def is_anonymous(self):
        return self.is_guest
    
    def __eq__(self, other):
        '''
        Checks the equality of two `UserMixin` objects using `get_id`.
        '''
        if isinstance(other, UserMixin):
            return self.get_id() == other.get_id()
        return NotImplemented

    def __ne__(self, other):
        '''
        Checks the inequality of two `UserMixin` objects using `get_id`.
        '''
        equal = self.__eq__(other)
        if equal is NotImplemented:
            return NotImplemented
        return not equal

    def get_id(self):
        return unicode(self.id)

    def __unicode__(self):
        return u"{} \"{}\" ({}:{})".format(self.login_name, self.display_name if self.display_name else "",
                                     self.authenticator_info.auth_type,
                                     self.authenticator_info.name)

    def __repr__(self):
        return u"User<{} '{}'> ({})".format(self.id, self.login_name, object.__repr__(self)).encode("utf8")

    __table_args__ = (UniqueConstraint(login_name, authenticator_id),)


class UserToUserGroup(DeclarativeBase, TimeStamp):

    __tablename__ = "user_to_usergroup"

    user_id = C(FK(User.id, ondelete="CASCADE"), primary_key=True)
    usergroup_id = C(FK(UserGroup.id, ondelete="CASCADE"), primary_key=True)
    managed_by_authenticator = C(Boolean, server_default="false")
    private = C(Boolean, server_default="false")

    user = rel(User, backref=bref("group_assocs", passive_deletes=True, cascade="all, delete-orphan"))
    usergroup = rel(UserGroup, backref=bref("user_assocs", passive_deletes=True, cascade="all, delete-orphan"))

    __table_args__ = (
        # This exclude constraint is something like a unique constraint only for rows where private is true.
        # Postgres doesn't support WHERE for unique constraints (why?), so lets just use this.
        # Alternatively, we could use a unique partial index to enforce the constraint.
        ExcludeConstraint((user_id, "="),
                          using="btree",
                          where="private = true",
                          name="only_one_private_group_per_user"),
        ExcludeConstraint((usergroup_id, "="),
                          using="btree",
                          where="private = true",
                          name="only_one_user_per_private_group"),
        # XXX: missing constraint: groups cannot be used elsewhere if they are private
    )

class OAuthUserCredentials(DeclarativeBase, TimeStamp):

    __tablename__ = "oauth_user_credentials"

    oauth_user = C(Unicode, primary_key=True)
    oauth_key = C(Unicode)
    user_id = integer_fk(User.id)

    user = rel(User)

