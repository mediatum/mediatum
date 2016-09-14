# -*- coding: utf-8 -*-
"""
    Database content validation.

    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
import logging
from sqlalchemy.orm.exc import NoResultFound
from core.database.postgres.user import UserGroup
from core import config, User


logg = logging.getLogger(__name__)

class InvalidDatabase(Exception):
    pass


def check_database():
    """Runs various startup checks for common data problems.
    Only database-independent content checks are done here.
    Structural validity of the database should be checked by the database connector.
    """
    from core.systemtypes import Root
    from core import db, Node
    q = db.query
    # root check
    possible_root_nodes = q(Root).all()
    if not possible_root_nodes:
        node_count = q(Node).count()
        if node_count == 0:
            raise InvalidDatabase("the database doesn't contain any nodes"\
                            "\nHINT: Did you forget to load initial data or import a database dump?"\
                            " Run 'bin/manage.py data init' to load basic data needed for mediaTUM operations.")
        else:
            raise InvalidDatabase("corrupt database: node table contains nodes, but no root node.")

    elif len(possible_root_nodes) > 1:
            raise InvalidDatabase("corrupt database: node table contains multiple root nodes.")

    # user check
    guest_user_login_name = config.get_guest_name()
    possible_guest_users = q(User).filter_by(login_name=guest_user_login_name).all()
    if not possible_guest_users:
        raise InvalidDatabase("guest user named '" + guest_user_login_name +"' not found."\
                        "\nHINT: Check user.guestuser setting. The value must be a login_name of an user.")

    if len(possible_guest_users) > 1:
        raise InvalidDatabase("multiple guest users named '" + guest_user_login_name +"' found."\
                        "\nHINT: Check user.guestuser setting. The value must be the login_name of a single user.")

    some_admin_group = q(UserGroup).filter_by(is_admin_group=True).first()
    if not some_admin_group:
        logg.warn("no admin group found. This works, but normally you should define at least one admin group.")


