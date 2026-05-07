# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""rename_bibtex_mask

Revision ID: aa19d5c8c132
Revises: 8c9d604339be
Create Date: 2026-02-27 09:35:57.373028

"""

from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from itertools import imap as map
from itertools import ifilter as filter
range = xrange

import logging as _logging
import os as _os
import sys as _sys

_sys.path.append(_os.path.abspath(_os.path.join(_os.path.dirname(__file__), "../..")))

import core as _core
import core.database.postgres.node as _
import core.init as _
_core.init.full_init()
import core.nodecache as _
import schema as _schema
import schema.mapping as _
import schema.schema as _
import utils as _utils
import utils.utils as _

# revision identifiers, used by Alembic.
revision = 'aa19d5c8c132'
down_revision = u'8c9d604339be'
branch_labels = None
depends_on = None

_logg = _logging.getLogger(__name__)


def _clone_node(node, new_name=None):
    new_name = new_name or node.name
    newnode = node.get_class_for_typestring(node.type)(new_name)
    _core.db.session.add(newnode)
    newnode.schema = node.schema
    newnode.orderpos = node.orderpos
    newnode.attrs.update(node.attrs)
    newnode.system_attrs.update(node.system_attrs)
    for access_ruleset in node.access_ruleset_assocs:
        if access_ruleset.private:
            ruleset = newnode.get_or_add_special_access_ruleset(ruletype=access_ruleset.ruletype)
            for rule_assoc in access_ruleset.ruleset.rule_assocs:
                ruleset.rule_assocs.append(_core.database.postgres.permission.AccessRulesetToRule(rule=rule_assoc.rule))
        else:
            newnode.access_ruleset_assocs.append(_core.database.postgres.permission.NodeToAccessRuleset(
                ruleset_name=access_ruleset.ruleset_name,
                ruletype=access_ruleset.ruletype,
                invert=access_ruleset.invert,
                blocking=access_ruleset.blocking,
                private=access_ruleset.private,
               ))
    return newnode


def _copy_maskitems(node, new_node, old_new_mapping):
    for maskitem in node.children.filter(_core.database.postgres.node.Node.type == 'maskitem'):
        new_maskitem = _clone_node(maskitem)
        new_node.children.append(new_maskitem)
        _copy_maskitems(maskitem, new_maskitem, old_new_mapping)
        new_maskitem.set("mappingfield", str(old_new_mapping[int(maskitem.attrs['mappingfield'])]))


def _get_node_for_attr(schema, node, attrname):
    try:
        nid = int(node.get(attrname))
    except ValueError:
        _logg.warning("%s (%s): %s %s has invalid %s", schema.name, schema.id, node.type, node.id, attrname)
        return
    return _core.db.query(_core.database.postgres.node.Node).get(nid)


def _copy_mask(schema, old_name, new_name):
    mask = schema.get_mask(old_name)
    if not mask:
        return
    exportmapping = _get_node_for_attr(schema, mask, "exportmapping")
    if not exportmapping:
        return

    for maskitem in mask.all_maskitems:
        attribute = _get_node_for_attr(schema, maskitem, "attribute")
        mappingfield = _get_node_for_attr(schema, maskitem, "mappingfield")
        if not ((attribute in schema.getMetaFields()) and (mappingfield in exportmapping.children)):
            _logg.warning("%s (%s): cannot copy invalid mask '%s' (%s) to '%s'",
                          schema.name, schema.id, old_name, mask.id, new_name)
            return
    mappings = _core.nodecache.get_mappings_node()
    new_mapping = _clone_node(exportmapping, "{}-{}-{}".format(new_name, schema.name, _utils.utils.gen_secure_token(128)))
    mappings.children.append(new_mapping)

    # copy mappingfields
    old_new_mapping = {}
    for mappingfield in exportmapping.children:
        new_mappingfield = _clone_node(mappingfield)
        new_mapping.children.append(new_mappingfield)
        old_new_mapping[mappingfield.id] = new_mappingfield.id

    new_mask = _clone_node(mask, new_name)
    schema.children.append(new_mask)
    _copy_maskitems(mask, new_mask, old_new_mapping)
    new_mask.set("exportmapping", str(new_mapping.id))
    return new_mask


def _rename_mask(schema, old_name, new_name):
    """
    Rename the schema's mask named `old_name` to `new_name`,
    and return the renamed mask.
    If `old_name` does not exist, or `new_name` already exists,
    do and return nothing.
    """
    mask = schema.get_mask(old_name)
    if not mask:
        return
    if schema.get_mask(new_name):
        _logg.warning("%s (%s): mask '%s' (%s) not renamed, as target name '%s' already exists",
                  schema.name, schema.id, old_name, mask.id, new_name)
        return
    _logg.info("%s (%s): rename mask '%s' (%s) in '%s'", schema.name, schema.id, old_name, mask.id, new_name)
    mask.name = new_name
    return mask


def upgrade():
    for schema in _core.db.query(_schema.schema.Metadatatype):
        mask = _rename_mask(schema, 'bibtex_import', 'import-bibtex')
        if not mask:
            mask = _copy_mask(schema, 'bibtex', 'import-bibtex')
            if not mask:
                continue
        for maskitem in mask.all_maskitems:
            if 'mappingfield' in maskitem and maskitem.get("fieldtype") == "mapping":
                # The `mappingfield` must not fall out of scope and
                # become liable to Python's garbage collection before
                # its `.attrs` have been modified, so we assign it
                # to a separate variable here before changing it.
                mappingfield = _core.db.query(_schema.mapping.MappingField).get(maskitem["mappingfield"])
                mappingfield.attrs.pop("exportformat", None)

    _core.db.session.commit()


def downgrade():
    for schema in _core.db.query(_schema.schema.Metadatatype):
        _rename_mask(schema, 'import-bibtex', 'bibtex_import')
    _core.db.session.commit()
