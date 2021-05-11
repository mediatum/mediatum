# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
common methods for list metatype's: list, mlist, dlist
"""

from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from itertools import imap as map
from itertools import ifilter as filter
range = xrange

import collections as _collections
import logging as _logging
import operator as _operator

import backports.functools_lru_cache as _backports_functools_lru_cache
import sqlalchemy as _sqlalchemy

import core as _core
import core.database.postgres as _database__postgres
import utils.utils as _utils


logg = _logging.getLogger(__name__)
_Element = _collections.namedtuple("_Element", "opt indent item count");


def count_list_values_for_all_content_children(collection_id, attribute_name):
    """
    returns an iterator of tuples (attribute-value, count) for a given attribute_name
    below a collection
    :param collection_id:
    :param attribute_name:
    :return:
    """
    func_call = _database__postgres.mediatumfunc.count_list_values_for_all_content_children(collection_id, attribute_name)
    stmt = _sqlalchemy.sql.select([_sqlalchemy.sql.text("*")], from_obj=func_call)
    res = _core.db.session.execute(stmt)
    return map(_operator.itemgetter(0,1), res.fetchall())


def format_elements(elements, field, values=(), node=None):
    """
    returns a list of html option, -group, -selected for {m,d,}lists
    listelements starts with '*' are preceded with a &nbsp;
    :param elements: iterator with all list elements
    :param field: metafield
    :param value: selected listelement
    :param node: node (optional)
    :return:
    """
    items = dict()
    if node:
        field_name = field.getName()
        items = dict(count_list_values_for_all_content_children(node.id, field_name))

    for value in elements:
        indent = len(value)-len(value.lstrip("*"))
        indentstr = 2 * max(0, indent-1) * "&nbsp;"
        value = value.lstrip("*")
        selectable = (not indent) or value.startswith(" ")
        value = value.strip()

        num = int(items.get(value, 0))
        if num<0:
            logg.error("num<0, using empty string")
        else:
            num = u" ({})".format(unicode(num)) if num else u""

        if not selectable:
            yield _Element(opt="optgroup", indent='<optgroup label="{}{}">'.format(indentstr,value), item="", count="")
        elif value in values:
            yield _Element(opt="optionselected", indent=indentstr, item=value, count=num)
        else:
            yield _Element(opt="option", indent=indentstr, item=value, count=num)
