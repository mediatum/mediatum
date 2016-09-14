# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from json import dumps
from sqlalchemy.dialects.postgresql.json import JSONElement


class Attributes(object):

    """
    Proxy for the attrs dict.
    Provides access to attribute values via dot notation.

    Examples:

    node.a.test == node.attrs["test"]
    """

    def __init__(self, obj, target_name):
        object.__setattr__(self, "getter", lambda: getattr(obj, target_name))

    def __getattr__(self, attr):
        return self.getter()[attr]


class PythonicJSONElement(JSONElement):

    """
    Wraps a JSONElement for a more pythonic experience in SQLAlchemy expression with JSON attributes.
    Operators behave differently depending on the type of the right operand.
    Nested dict / list structures are supported.

    Examples:

        q(Document).filter(Document.a.title == "Some Title").one()
        q(Image).filter(Image.a.height >= 600)
        q(Document).filter(Document.a.title.between("a", "c")) # lexicographical order!

    => finds all documents with given title.
    """

    def __init__(self, left, right, *args, **kwargs):
        if hasattr(right, "__iter__"):
            self._path = list(right)
        else:
            self._path = [right]
        super(PythonicJSONElement, self).__init__(left, right, *args, **kwargs)

    def operate(self, op, *other, **kwargs):
        """This performs a JSON comparison (Postgres operator ->)."""
        if len(other) == 1:
            # this is just a optimization for special cases to avoid calling the JSON dump function; the final return is sufficient
            other = other[0]
            if isinstance(other, bool):
                return super(JSONElement, self).operate(op, str(other).lower())
            elif isinstance(other, (int, long)):
                return super(JSONElement, self).operate(op, str(other))
            elif other is None:
                return super(JSONElement, self).operate(op, None, **kwargs)
            return super(JSONElement, self).operate(op, dumps(other), **kwargs)
        # multiple operands given
        return super(JSONElement, self).operate(op, *(dumps(o) for o in other), **kwargs)

    # specialized text operators

    def like(self, other, **kwargs):
        return self.astext.like(other, **kwargs)

    def contains(self, other, **kwargs):
        return self.astext.contains(other, **kwargs)

    def startswith(self, other, **kwargs):
        return self.astext.startswith(other, **kwargs)

    def endswith(self, other, **kwargs):
        return self.astext.endswith(other, **kwargs)

    def match(self, other, **kwargs):
        return self.astext.match(other, **kwargs)

    @property
    def json(self):
        return JSONElement(self.left, self._path)

    def __getattr__(self, name):
        # XXX: could cause some exceptions when SQLAlchemy tries to check for attributes with getattr()
        if name.startswith("_") or name in ("is_literal", "key"):
            return object.__getattribute__(self, name)
        return PythonicJSONElement(self.left, self._path + [name])

    def __getitem__(self, item):
        if hasattr(item, "__iter__"):
            return PythonicJSONElement(self.left, self._path + list(item))
        else:
            return PythonicJSONElement(self.left, self._path + [item])


class AttributesExpressionAdapter(object):

    """
    Allows "natural" access to attributes in SQLAlchemy expressions, see `PythonicJSONElement`.

    """

    def __init__(self, obj, target_name):
        object.__setattr__(self, "getter", lambda: getattr(obj, target_name))

    def __getattr__(self, attr):
        return PythonicJSONElement(self.getter(), attr)

    def __getitem__(self, item):
        if hasattr(item, "__iter__"):
            return PythonicJSONElement(self.getter(), list(item))
        return PythonicJSONElement(self.getter(), item)
