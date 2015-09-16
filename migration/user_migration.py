# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
import logging
from core import db, Node, User
from contenttypes import Directory, Home
from core.translation import getDefaultLanguage, translate

logg = logging.getLogger(__name__)

q = db.query


def migrate_home_dirs(orphan_dir_id):
    """ Moves orphaned home dirs (not associated with an user) to a directory with id `orphan_dir_id`.
        The remaining home dirs are renamed: Arbeitsverzeichnis(<name>) -> <user_login_name>_<user_id>.
    """
    home_root = q(Home).one()
    orphan_dir = q(Directory).get(orphan_dir_id)

    for home_dir in home_root.children:
        # XXX: fix DB later, we have multiple users for a single home dir
        user = q(User).filter_by(home_dir_id=home_dir.id).first()

        if user is None:
            logg.info("orphaned home dir %s (%s)", home_dir.name, home_dir.id)
            home_dir[u"system.migration"] = u"moved by mysql -> postgres migration"
            home_root.children.remove(home_dir)
            orphan_dir.container_children.append(home_dir)

        else:
            logg.info("home dir %s (%s) -> user login_name=%s (%s)", home_dir.name, home_dir.id, user.login_name, user.id)
            home_dir.name = u"{}_{}".format(user.id, user.login_name)
            home_dir[u"system.used_as"] = u"home"


def migrate_special_dirs():
    """Special dirs are found by special attribute system.used_as, not the directory name as before.
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

                dirr[u"system.used_as"] = new
