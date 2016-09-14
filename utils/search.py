# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""

import logging
from sqlalchemy import func as sqlfunc
from core import db, File
from contenttypes import Data

q = db.query
logg = logging.getLogger(__name__)


def import_node_fulltext(node, overwrite=False):
    s = db.session

    if not overwrite and node.fulltext:
        logg.info("node %s already has a fulltext, not overwriting it", node.id)
        return False

    fulltext_files = node.files.filter_by(filetype=u"fulltext")
    fulltexts = []

    for fi in fulltext_files:
        if fi.exists:
            with fi.open() as f:
                try:
                    fulltexts.append(f.read())
                except UnicodeDecodeError:
                    logg.info("decoding error for node %s from %s", node.id, fi.path)
                    continue

            logg.info("imported fulltext for node %s from %s", node.id, fi.path)
        else:
            logg.warn("missing fulltext for node %s from %s", node.id, fi.path)

    if fulltexts:
        node.fulltext = u"\n---\n".join(fulltexts)
        s.commit()
        return True

    return False


def import_fulltexts(overwrite=False, mod_n=None, mod_i=None):
    nodes = q(Data).filter(Data.files.any(File.filetype == "fulltext")).order_by(Data.id)
    
    if mod_n:
        if mod_i is None:
            raise Exception("mod_i must be specified when mod_n is given!")
        
        nodes = nodes.filter(sqlfunc.mod(Data.id, mod_n) == mod_i)

    # don't overwrite = ignore nodes that have a fulltext
    if not overwrite:
        nodes = nodes.filter_by(fulltext=None)

    import_count = 0
    for node in nodes:
        imported = import_node_fulltext(node, overwrite=overwrite)
        if imported:
            import_count += 1

    return import_count
