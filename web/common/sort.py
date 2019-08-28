"""
 mediatum - a multimedia content repository

 Copyright (C) 2019 Kerstin Lahr <Kerstin.Lahr@ub.tum.de>

 This program is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.

 This program is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import operator as _operator

from core.translation import t as _t
from core import Node as _Node
from core import db as _db
from schema.schema import Metadatatype as _Metadatatype
from sqlalchemy import func as _func

q = _db.query

class SortChoice(object):
    """
    Class for a list of SortChoices used as dropdown options in editor and frontend.
    Used also by content_nav_list_header.j2.jade
    """
    def __init__(self, label, value, descending=False, selected_value=None):
        super(SortChoice, self).__init__()
        self.label = label
        self.value = value
        self.descending = descending
        self.isselected = self.value == selected_value

    def getLabel(self):
        return self.label

    def getName(self):
        return self.value

    def selected(self):
        return "selected" if self.isselected else None

def get_sort_choices(container=None, metadatatype=None, off="", t_off="", t_desc=None, selected_value=None):
    """
    Function to yield back the sortchoices for the dropdown selection of available sortfields in
    specified container or for specified metadatatype.
    Must be given either a container OR a metadatatype.
    """

    assert t_desc>""  # check that it is an non-empty string
    assert bool(container)!=bool(metadatatype)  # only accept either, container or metadatatype!

    if metadatatype:
        metadatatypes = (metadatatype,)
    else:
        schemanames = container.all_children_by_query(
            q(_Node.schema)
            .filter_by(subnode=False)
            .group_by(_Node.schema)
            .order_by(_func.count(_Node.schema).desc())
        )
        metadatatypes = (q(_Metadatatype).filter_by(name=s[0]).one() for s in schemanames)

    yield SortChoice(t_off, off, False, "not selected" if selected_value else "")
    for m in metadatatypes:
        result = tuple(_get_metadata_type_for_sort(m, t_desc, selected_value))
        if result:
            for r in result:
                yield r
            return


def _get_metadata_type_for_sort(metadatatype, t_desc, selected_value=None):
    """
    Takes a metadatatype and yields back all SortChoices for that metadatatype sorted by name.
    Per sortfield two SortChoices - in ascending and descending order, respectively.
    """
    fields = metadatatype.metafields.all()
    fields = filter(_operator.methodcaller("Sortfield"), fields)
    fields = sorted(fields, key=_operator.attrgetter("name"))
    for field in fields:
        yield SortChoice(               field.label,                        field.name , False, selected_value)
        yield SortChoice(u"{}{}".format(field.label, t_desc), u"-{}".format(field.name), False, selected_value)
