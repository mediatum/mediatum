# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from json import dumps
from sqlalchemy import types as sqltypes
from sqlalchemy.sql import elements, default_comparator
from sqlalchemy.sql.operators import custom_op
from sqlalchemy import util


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


# JSONElement not defined in sqlalchemy 1.2.3
# from sqlalchemy/dialects/postgresql/json.py   sqlalchemy 1.0.15
class JSONElement(elements.BinaryExpression):
    """Represents accessing an element of a :class:`.JSON` value.

    The :class:`.JSONElement` is produced whenever using the Python index
    operator on an expression that has the type :class:`.JSON`::

        expr = mytable.c.json_data['some_key']

    The expression typically compiles to a JSON access such as ``col -> key``.
    Modifiers are then available for typing behavior, including
    :meth:`.JSONElement.cast` and :attr:`.JSONElement.astext`.

    """

    def __init__(self, left, right, astext=False,
                 opstring=None, result_type=None):
        self._astext = astext
        if opstring is None:
            if hasattr(right, '__iter__') and \
                    not isinstance(right, util.string_types):
                opstring = "#>"
                right = "{%s}" % (
                    ", ".join(util.text_type(elem) for elem in right))
            else:
                opstring = "->"

        self._json_opstring = opstring
        operator = custom_op(opstring, precedence=5)
        right = default_comparator._check_literal(
            left, operator, right)
        super(JSONElement, self).__init__(
            left, right, operator, type_=result_type)

    @property
    def astext(self):
        """Convert this :class:`.JSONElement` to use the 'astext' operator
        when evaluated.

        E.g.::

            select([data_table.c.data['some key'].astext])

        .. seealso::

            :meth:`.JSONElement.cast`

        """
        if self._astext:
            return self
        else:
            return JSONElement(
                self.left,
                self.right,
                astext=True,
                opstring=self._json_opstring + ">",
                result_type=sqltypes.String(convert_unicode=True)
            )

    def cast(self, type_):
        """Convert this :class:`.JSONElement` to apply both the 'astext' operator
        as well as an explicit type cast when evaluated.

        E.g.::

            select([data_table.c.data['some key'].cast(Integer)])

        .. seealso::

            :attr:`.JSONElement.astext`

        """
        if not self._astext:
            return self.astext.cast(type_)
        else:
            return sql.cast(self, type_)


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
