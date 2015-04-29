# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from sqlalchemy import Integer, Unicode, Text, Boolean, Table, DateTime
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import ARRAY

from core.database.postgres import DeclarativeBase, db_metadata
from core.database.postgres import rel, bref, C, FK
from sqlalchemy_utils.types import EmailType
from core.database.postgres import TimeStamp, integer_fk, integer_pk


class AuthenticatorInfo(DeclarativeBase):

    __tablename__ = "authenticator"

    id = integer_pk()
    name = C(Unicode)
    auth_type = C(Text)


user_to_usergroup = Table("user_to_usergroup", db_metadata,
                          integer_fk("user.id", name="user_id"),
                          integer_fk("usergroup.id", name="usergroup_id")
                          )


class UserGroup(DeclarativeBase, TimeStamp):

    __tablename__ = "usergroup"

    id = integer_pk()
    name = C(Unicode)
    description = C(Unicode)
    hidden_edit_functions = C(ARRAY(Unicode))

    can_edit = C(Boolean)
    can_edit_workflow = C(Boolean)

    def __repr__(self):
        return u"UserGroup<{} '{}'> ({})".format(self.id, self.name, object.__repr__(self)).encode("utf8")

class User(DeclarativeBase, TimeStamp):

    __tablename__ = "user"

    name = C(Unicode)
    id = integer_pk()
    lastname = C(Unicode)
    firstname = C(Unicode)
    telephone = C(Unicode)
    organisation = C(Unicode)
    comment = C(Unicode)
    email = C(EmailType)
    password = C(Text)

    # user activity
    last_login = C(DateTime)
    active = C(Boolean)

    # options
    can_change_password = C(Boolean)
    can_edit_shoppingbag = C(Boolean)

    # relationships
    groups = rel(UserGroup, secondary=user_to_usergroup, backref='users')

    shoppingbag_id = integer_fk("node.id")
    shoppingbag = rel("ShoppingBag", foreign_keys=[shoppingbag_id])

    home_dir_id = integer_fk("node.id")
    home_dir = rel("Directory", foreign_keys=[home_dir_id])

    authenticator_info = rel(AuthenticatorInfo)
    authenticator_id = integer_fk(AuthenticatorInfo.id)

    @property
    def group_ids(self):
        return [g.id for g in self.groups] + [self.id]

    def __repr__(self):
        return u"User<{} '{}'> ({})".format(self.id, self.name, object.__repr__(self)).encode("utf8")
