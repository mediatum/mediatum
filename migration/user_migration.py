# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
import logging
from core import db, Node
from contenttypes import Directory, Home
from core.translation import getDefaultLanguage, translate

logg = logging.getLogger(__name__)

q = db.query


def migrate_special_dirs():
    """Special dirs are found by special attribute system.used_as, not the directory name.
    """
    home_root = q(Home).one()
    for home_dir in home_root.children:
        logg.info("home dir %s %s", home_dir.id, home_dir.name)
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
