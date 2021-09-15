# -*- coding: utf-8 -*-
"""
    Data access objects for API results.
    
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from __future__ import division

import logging as _logging
from itertools import imap
from munch import Munch


logg = _logging.getLogger(__name__)

class APINode(Munch):

    """Represents a node retrieved via the JSON export API
    """

    def __init__(self, id, attrs):
        self.id = id
        self.attrs = Munch(attrs)
        if "nodename" in attrs:
            del self.attrs["nodename"]
            self.name = attrs.get("nodename")
        else:
            self.name = None

    @classmethod
    def from_dict(self, d):
        return APINode(d["id"], d["attributes"])

    def __repr__(self):
        return "APINode #{}".format(self.id)

    def __getitem__(self, key):
        try:
            return super(APINode, self).__getitem__(key)
        except KeyError:
            return self.attrs[key]

    def get(self, key, default=None):
        return self.attrs.get(key, default)

    def toJSON(self, **kwargs):
        # returns escaped str by default, we want unicode
        kwargs["ensure_ascii"] = False
        return super(APINode, self).toJSON(**kwargs)

    def toYAML(self, **kwargs):
        # returns escaped str by default, we want unicode
        if "allow_unicode" not in kwargs:
            kwargs["allow_unicode"] = True
        if "encoding" not in kwargs:
            kwargs["encoding"] = None
        return super(APINode, self).toYAML(**kwargs)


class APIShortlist(object):

    """Represents a *shortlist*.
    Shortlists are lists containing tuples of (pos, node id, name, type)
    """

    def __init__(self, shortlist):
        self.shortlist = shortlist

    def iterids(self):
        return (e[1] for e in self.shortlist)

    def iternames(self):
        return (e[2] for e in self.shortlist)

    def itertypes(self):
        return (e[3] for e in self.shortlist)

    def iteritems(self):
        return (e[1:] for e in self.shortlist)

    def __iter__(self):
        return self.iterids()

    def __len__(self):
        return len(self.shortlist)


class NodeAPIResult(object):

    """Generic representation of a result from a call to the export API.
    """

    def __init__(self, data):
        if "nodelist" in data:
            self.nodelist = data["nodelist"]
            del data["nodelist"]
        if "result_shortlist" in data:
            self.shortlist = APIShortlist(data["result_shortlist"])
            del data["result_shortlist"]
        self.info = Munch(data)

    def __getitem__(self, key):
        return self.info[key]

    def __getattr__(self, name):
        return self.info.__getattr__(name)

    def iternode(self):
        return imap(APINode.from_dict, (l[0] for l in self.nodelist))

    def print_info(self):
        logg.info("%s", self.info.toYAML())
