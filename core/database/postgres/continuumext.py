# -*- coding: utf-8 -*-
"""
    Extensions for the sqlalchemy-continuum package

    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""

import types
from sqlalchemy_continuum.utils import parent_class
from werkzeug.utils import cached_property


class MtVersionBase(object):

    @classmethod
    def parent_class(cls):
        return parent_class(cls)

    def __getattr__(self, key):
        FORBIDDEN_ATTRS = ("__versioned__", "_sa_instance_state", "_proxy_dicts")
        if key in FORBIDDEN_ATTRS:
            raise AttributeError()

        parent_cls = self.parent_class()
        attr = getattr(parent_cls, key)
        if isinstance(attr, types.MethodType):
            return types.MethodType(attr.__func__, self, parent_cls)
        elif isinstance(attr, property):
            return attr.fget(self)
        elif isinstance(attr, cached_property):
            return attr.__get__(self)

        return attr

    @property
    def tag(self):
        return self.transaction.meta.get(u"tag")

    @tag.setter
    def tag(self, tag):
        self.transaction.meta[u"tag"] = tag

    @property
    def comment(self):
        return self.transaction.meta.get(u"comment")

    @comment.setter
    def comment(self, comment):
        self.transaction.meta[u"comment"] = comment
