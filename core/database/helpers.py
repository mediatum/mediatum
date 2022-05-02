# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from __future__ import division
from __future__ import print_function

from warnings import warn
from sqlalchemy.ext.declarative import declared_attr

from core import db
from core.database.postgres.node import children_rel


q = db.query


class ContainerMixin(object):

    @declared_attr
    def container_children(self):
        return children_rel("Container")

    def getContainerChildren(self):
        warn("deprecated, use Node.container_children instead", DeprecationWarning)
        return self.container_children
