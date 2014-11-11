# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from warnings import warn


def check_type_arg_for_systemtype(cls):
    clsname = cls.__name__

    def init(self, name="", type=None, id=None, attrs=None, orderpos=None):
        if type is None:
            type = clsname.lower()
        else:
            warn("type param is deprecated for " + clsname + " instances", DeprecationWarning)
            if not type == clsname.lower():
                raise ValueError("type must be {} for a {} instance ".format(clsname.lower(), clsname))

        super(cls, self).__init__(name, type, id, None, attrs, orderpos)

    cls.__init__ = init
    return cls


def check_type_arg_for_contenttype(cls):
    clsname = cls.__name__

    def init(self, name="", type=None, id=None, schema=None, attrs=None, orderpos=None):
        if type is None:
            type = clsname.lower()
        else:
            warn("type param is deprecated for " + clsname + " instances", DeprecationWarning)
            if not type.startswith(clsname.lower()):
                raise ValueError("type must be {} for a {} instance ".format(clsname.lower(), clsname))

        super(cls, self).__init__(name, type, id, schema, attrs, orderpos)

    cls.__init__ = init
    return cls


