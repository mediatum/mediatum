# -*- coding: utf-8 -*-

# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

from warnings import warn


def check_type_arg(cls):
    from core.database.postgres.node import Node

    def init(self, name=u"", type=None, id=None, attrs=None, system_attrs=None, orderpos=None):
        clsname = self.__class__.__name__

        if type is None:
            type = unicode(clsname.lower())
        else:
            warn("type param is deprecated for " + clsname + " instances", DeprecationWarning)
            if not type == clsname.lower():
                raise ValueError("type must be {} for a {} instance ".format(clsname.lower(), clsname))

        Node.__init__(self, name, type, id, None, attrs, system_attrs, orderpos)

    cls.__init__ = init
    return cls


def check_type_arg_with_schema(cls):
    from core.database.postgres.node import Node


    def init(self, name=u"", type=None, id=None, schema=None, attrs=None, system_attrs=None, orderpos=None):
        clsname = self.__class__.__name__

        if type is None:
            type = unicode(clsname.lower())
        else:
            warn("type param is deprecated for " + clsname + " instances", DeprecationWarning)
            if not type.startswith(clsname.lower()):
                raise ValueError("type must be {} for a {} instance ".format(clsname.lower(), clsname))

        if schema is None:
            schema = type

        Node.__init__(self, name, type, id, schema, attrs, system_attrs, orderpos)

    cls.__init__ = init
    return cls
