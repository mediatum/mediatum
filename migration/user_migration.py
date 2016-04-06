# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
import logging
from sqlalchemy import text
from core import config, db, Node, User
from contenttypes import Directory, Home
from core.translation import getDefaultLanguage, translate
from sqlalchemy.orm.exc import NoResultFound

logg = logging.getLogger(__name__)

q = db.query


def migrate_home_dirs(orphan_dir_id):
    """ Moves orphaned home dirs (not associated with an user) to a directory with id `orphan_dir_id`.
        The remaining home dirs are renamed: Arbeitsverzeichnis(<name>) -> <user_login_name>_<user_id>.
    """
    s = db.session
    home_root = q(Home).one()
    orphan_dir = q(Directory).get(orphan_dir_id)

    for home_dir in home_root.children:
        # XXX: fix DB later, we have multiple users for a single home dir
        user = q(User).filter_by(home_dir_id=home_dir.id).first()

        if user is None:
            logg.info("orphaned home dir name=%s id=%s", home_dir.name, home_dir.id)
            home_dir.system_attrs[u"migration"] = u"moved by mysql -> postgres migration"
            # we go "low-level" here because we don't want to trigger noderelation updates via nodemapping
            s.execute(text("DELETE FROM noderelation WHERE cid=:cid").bindparams(cid=home_dir.id))
            s.execute(text("INSERT INTO noderelation VALUES(:nid, :cid, 1)").bindparams(nid=orphan_dir.id, cid=home_dir.id))
        else:
            new_name = u"{}_{}".format(user.id, user.login_name)
            if home_dir.name == new_name:
                logg.info("home dir name=%s id=%s already renamed", home_dir.name, home_dir.id)
            else:
                logg.info("renaming home dir name=%s id=%s associated with user login_name=%s id=%s",
                          home_dir.name, home_dir.id, user.login_name, user.id)
                home_dir.name = new_name

            home_dir.system_attrs[u"used_as"] = u"home"


def migrate_special_dirs():
    """Special dirs are found by special system attribute used_as, not the directory name as before.
    """
    home_root = q(Home).one()
    for home_dir in home_root.children:
        logg.info("fixing special dirs in home dir %s (%s)", home_dir.name, home_dir.id)
        lang = getDefaultLanguage()
        special_dirs = [
            (translate(u"user_trash", lang), u"trash"),
            (translate(u"user_faulty", lang), u"faulty"),
            (translate(u"user_upload", lang), u"upload")
        ]

        for old, new in special_dirs:
            new_dir = home_dir.children.filter_by(name=new).scalar()
            if not new_dir:
                old_dirrs = home_dir.children.filter_by(name=old).order_by(Node.id).all()
                if not old_dirrs:
                    dirr = Directory(new)
                    home_dir.children.append(dirr)
                else:
                    if len(old_dirrs) > 1:
                        logg.warn("%s special dirs found for %s, using oldest dir", len(old_dirrs), home_dir.name)
                    dirr = old_dirrs[0]
                    dirr.name = new

                dirr.system_attrs[u"used_as"] = new


def set_admin_group():
    from core import UserGroup
    admin_group_name = config.get(u"user.admingroup", u"administration")
    try:
        admin_group = q(UserGroup).filter_by(name=admin_group_name).one()
    except NoResultFound:
        logg.warn("admin group '%s' specified in config file does not exist, no admin group set!")

    admin_group.is_admin_group = True
    admin_group.is_workflow_editor_group = True
    admin_group.is_editor_group = True


def rehash_md5_password_hashes():
    """Double-hash unsalted md5 hashes for internal users with our new hashing alg scrypt"""
    for user in q(User).filter_by(authenticator_id=0):
        if user.password_hash:
            if not user.salt:
                user.change_password(user.password_hash)
                logg.info("rehashing md5 for user: %s", user.id)
            else:
                logg.info("user already has a secure password hash: %s", user.id)
        else:
            logg.warn("internal user has no password: %s", user.id)
