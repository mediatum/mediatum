# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from warnings import warn

from core import db
from core.database.postgres.model import child_rel_options, rel
from sqlalchemy.ext.declarative import declared_attr


q = db.query


class ContainerTypeMixin(object):
    @declared_attr
    def container_children(self):
        return rel("ContainerType", **child_rel_options)

    def getContainerChildren(self):
        warn("deprecated, use Node.container_children instead", DeprecationWarning)
        return self.container_children
