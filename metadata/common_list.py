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

import operator as _operator

import sqlalchemy as _sqlalchemy

import core as _core
import core.database.postgres as _database__postgres


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
