# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details

    Migrate old node version to sqlalchemy-continuum
"""
from core import db
from migration.import_datamodel import Node as ImportNode, NodeAttribute
q = db.query


def all_version_nodes():
    return q(ImportNode).join(NodeAttribute).filter((NodeAttribute.name == "system.prev_id") & NodeAttribute.value != "")