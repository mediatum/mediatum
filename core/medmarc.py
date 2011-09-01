"""
 mediatum - a multimedia content repository

 Copyright (C) 2011 Stefan Behnel <stefan_ml@behnel.de>

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
import re

from itertools import chain, groupby # requires Python 2.4
from operator import itemgetter
from urlparse import urlparse

import pymarc
from utils.utils import Template
from schema import schema, mapping

def _parse_protocol_indicator(field, subfields, _protocol_map={'http': '4', 'ftp': '1'}):
    """
    Parse MARC 856 protocol indicator from URL.
    """
    url = None
    for subfield, value in subfields:
        if subfield == 'u':
            url = value
            break
    if not url:
        return '#'
    parsed_url = urlparse(url)
    return _protocol_map.get(parsed_url.scheme, '#')

# MARC21 indicators by MARC field
_indicators = {
    '245' : [ # Title Statement
        '0', # Title added entry (0 - No added entry, 1 - Added entry)
        '0', # Nonfiling characters (0 - No nonfiling characters, 1-9 - Number of nonfiling characters)
        ],
    '100' : [ # Main Entry-Personal Name
        '1', # Type of personal name entry element (0 - Forename, 1 - Surname, 3 - Family name)
        '#', # Undefined
        ],
    '653' : [ # Index Term-Uncontrolled
        '1', # Level of index term (# - No information provided, 0 - No level specified, 1 - Primary, 2 - Secondary)
        '0', # Type of term or name (# - No information provided, 0 - Topical term, 1 - Personal name,
             #                       2 - Corporate name, 3 - Meeting name, 4 - Chronological term,
             #                       5 - Geographic name, 6 - Genre/form term)
        ],
    '110' : [ # Main Entry-Corporate Name
        '1', # Type of corporate name entry element (0 - Inverted name, 1 - Jurisdiction name, 2 - Name in direct order)
        '#', # Undefined
        ],
    '260' : [ # Publication, Distribution, etc. (Imprint)
        '2', # Sequence of publishing statements (# - Not applicable/No information provided/Earliest available publisher,
             #                                    2 - Intervening publisher, 3 - Current/latest publisher
        '#', # Undefined
        ],
    '270' : [ # Address
        '1', # Level (# - No level specified, 1 - Primary, 2 - Secondary)
        '#', # Type of address (# - No type specified, 0 - Mailing, 7 - Type specified in subfield 'i')
        ],
    '020' : [ # International Standard Book Number (ISBN)
        '#', # Undefined
        '#', # Undefined
        ],
    '490' : [ # Series Statement
        '1', # Series tracing policy, 0 - Series not traced, 1 - Series traced
        '#', # Undefined
        ],
    '856' : [ # Electronic Location and Access
        _parse_protocol_indicator,
        # Access method (# - No information provided, 0 - Email, 1 - FTP, 2 - Remote login (Telnet), 3 - Dial-up,
        #                4 - HTTP, 7 - Method specified in subfield '2')
        '0', # Relationship  (# - No information provided, 0 - Resource, 1 - Version of resource,
             #                2 - Related resource, 8 - No display constant generated)
        ],
    }

def find_marc_mapping(schema_name):
    """
    Look up the MARC21 mapping configuration in the node tree.

    The ``schema_name`` is used to find the mapping configuration
    based on a naming convention, specifically ``marc21_XYZ`` for a
    schema name ``XYZ``.

    Each entry in the mapping has a name 'field$subfield'
    (e.g. '240$a') that indicates the MARC field and subfield the
    value is mapped to.  The 'description' attribute provides the
    template string that maps the node data to the specific field
    content.

    Returns a list of tuples:
    [ ((field, subfield), field_template), ... ]
    """
    marc_mapping = mapping.getMapping('marc21_' + schema_name)
    if marc_mapping is None: # FIXME: or not marc_mapping.isActive():
        return None

    mapping_fields = [ (tuple(mask_item.getName().split('$', 1)),
                        Template(mask_item.getDescription()))
                       for mask_item in marc_mapping.getFields()
                       if '$' in mask_item.getName() ]
    return mapping_fields

class MarcMapper(object):
    """
    MARC21 mapper that caches the parsed field mappings over its own
    lifetime.  More efficient than looking them up on each conversion.
    """
    def __init__(self):
        self.mappings_by_schema = {}

    def __call__(self, node):
        schema_name = node.getSchema()
        try:
            mapping_fields = self.mappings_by_schema[schema_name]
        except KeyError:
            mapping_fields = self.mappings_by_schema[schema_name] = \
                             find_marc_mapping(schema_name)
        if mapping_fields is None:
            return None
        return map_node(node, mapping_fields)

    def __repr__(self):
        return 'MarcMapper(%s)' % ', '.join(self.mappings_by_schema)

def map_node(node, mapping_fields=None):
    """
    Map a node to a MARC21 record.  Returns its serialised form.
    """
    if not mapping_fields:
        mapping_fields = find_marc_mapping(node.getSchema())
        if mapping_fields is None:
            raise LookupError(
                "Failed to find marc mappings for node %s with schema %s" % (
                    node.id, node.getSchema()))

    # interpolate MARC field value templates using node attributes
    fields = {}
    for (field, subfield), field_template in mapping_fields:
        value = field_template(node)
        if not value:
            continue
        if field not in fields:
            fields[field] = {}
        fields[field][subfield] = str(value)

    # build MARC record, adding field indicators accordingly
    record = pymarc.Record()
    for field, subfields in sorted(fields.iteritems()):
        subfields = sorted(subfields.iteritems())

        # determine MARC field indicators
        ind1 = ind2 = '#'  # == "undefined"
        indicators = _indicators.get(field)
        if indicators:
            ind1, ind2 = indicators
            # support custom indicator value extraction functions (e.g. for URLs)
            if callable(ind1):
                ind1 = ind1(field, subfields)
            if callable(ind2):
                ind2 = ind2(field, subfields)

        record.add_field(pymarc.Field(
            field, indicators=[ind1, ind2], subfields = list(chain(* subfields))))

    # serialise
    return record.as_marc()
