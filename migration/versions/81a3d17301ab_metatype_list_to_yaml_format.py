# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""metatype_list_to_yaml_format

Revision ID: 81a3d17301ab
Revises: ed88eef38764
Create Date: 2023-01-05 05:56:11.303235

"""

from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from itertools import imap as map
from itertools import ifilter as filter
range = xrange

import collections as _collections
import os as _os
import sys as _sys

_sys.path.append(_os.path.abspath(_os.path.join(_os.path.dirname(__file__), "../..")))

import core as _core
import core.init as _core_init
_core_init.full_init()
import schema.schema as _schema


# revision identifiers, used by Alembic.
revision = '81a3d17301ab'
down_revision = u'ed88eef38764'
branch_labels = None
depends_on = None


def _parse_item(item):
    element = dict(subelements=list())

    # count and strip prefix stars
    element["stars"] = len(item)
    item = item.lstrip("*")
    element["stars"] -= len(item)

    # detect and strip prefix space
    element["name"] = item.lstrip(" ")
    element["selectable"] = bool(item.startswith(" ") or not element["stars"])

    return element


def _clean_elements(elements):
    # clean "internal" data "stars"
    # turn simple elements into strings (selectable, no subelements)
    for element in elements:
        if element["selectable"] and not element["subelements"]:
            yield element["name"]
            continue
        del element["stars"]
        element["subelements"] = tuple(_clean_elements(element["subelements"]))
        yield element


def _upgrade_items(items):

    # path is a list of element structures:
    # its last element is the previously inserted one,
    # the elements before at the parents of the previously inserted one.
    # the first element is a top-level dummy element;
    # its subelements will be the list that is returned as real top-level structure
    path = [dict(stars=-1, subelements=list())]

    for element in map(_parse_item, items):

        # for the candidate `element` for insertion,
        # we go the path upwards from the lowest element to find
        # a suitable parent for the new `element`
        while True:
            parent = path.pop()

            # special case: if the candidate `element` has no stars,
            # it should be attached the next possible
            # previous parent if that one has stars
            if parent["stars"] > 0 and not element["stars"]:
                break

            # (still the same) special case:
            # if the parent element has no stars, but the `element`
            # does, the parent is actually one level *below*
            # the current element, and we have to skip it
            # (and likely also the next candidate)
            if element["stars"] and not parent["stars"]:
                continue

            # if a parent candidate has more stars than the `element`,
            # it can never be a parent of `element`
            if parent["stars"] > element["stars"]:
                continue

            # if a parent candidate has fewer stars than the `element`,
            # it certainly is the correct parent
            # (this will always accept the top-level dummy as
            # parent if all other elements are exhausted)
            if parent["stars"] < element["stars"]:
                break

            # the parent candidate has the same amount of stars as the `element`:
            # it can only be the real parent it is not selectable, while the `element` is
            if element["selectable"] and not parent["selectable"]:
                break

        # attach element to the parent
        parent["subelements"].append(element)
        path.extend((parent, element))

    return tuple(_clean_elements(path[0]["subelements"]))


def upgrade():
    for metafield in _core.db.query(_schema.Metafield).filter(_schema.Metafield.a.type == 'list').prefetch_attrs():
        data = metafield.metatype_data
        data['listelements'] = _upgrade_items(data['listelements'])
        metafield.metatype_data = data
    _core.db.session.commit()


def _downgrade_element(elements, _indent=1):
    for element in elements:
        if not isinstance(element, _collections.Mapping):
            assert element >= ""
            element = dict(
                name=element,
                selectable=True,
                subelements=(),
               )
        yield u"{}{}{}".format("*"*_indent, ' ' if element["selectable"] else '', element["name"])
        for e in _downgrade_element(element["subelements"], _indent + 1):
            yield e


def downgrade():
    for metafield in _core.db.query(_schema.Metafield).filter(_schema.Metafield.a.type == 'list').prefetch_attrs():
        data = metafield.metatype_data
        data['listelements'] = tuple(_downgrade_element(data['listelements']))
        metafield.metatype_data = data
    _core.db.session.commit()
