# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import json
import logging
import flask as _flask

from utils.utils import esc
from schema.schema import getMetaType
from web.services.serviceutils import attribute_name_filter


logg = logging.getLogger(__name__)


def buildNodeDescriptor(params, node, indent=None, written=None, children=True, parents=False):
    nd = []
    d = {}
    if written is None:
        written = {}

    nodedict = {}
    nodedict['id'] = node.id

    mask = params.get('mask', 'none').lower()

    attrlist = params.get('attrlist', [])
    if attrlist:
        attrlist = attrlist.split(',')

    attrspec = params.get('attrspec', 'default_mask')
    # 'all': no restriction, send all attributes
    # 'none': to not send any attribute at all
    # 'default_mask' (default): only send attributes that correspond to the default mask fields
    #
    # remark: attributes specified comma separated in 'attrlist' are added to those specified by 'attrspec'
    #

    if mask == 'default':
        nodedict['defaultexport'] = node.show_node_text(labels=1, language=params.get('lang', ''))
    elif mask not in ["", "none"]:  # deliver every mask
        try:
            mask_obj = getMetaType(node.getSchema()).getMask(mask)
            if mask_obj:
                nodedict['defaultexport'] = mask_obj.getViewHTML([node], flags=8)
            else:
                nodedict['defaultexport'] = "mask not found"
        except Exception as e:
            logg.exception("exception in buildNodeDescriptor")
            nodedict['defaultexport'] = "error"

    if children:
        nodedict['children'] = []
        for c in node.getChildren().sort_by_orderpos():
            nodedict['children'].append({'id': ustr(c.id), 'type': c.type, 'name': esc(c.name)})

    if parents:
        nodedict['parents'] = []
        for c in node.getParents().sort_by_orderpos():
            nodedict['parents'].append({'id': ustr(c.id), 'type': c.type, 'name': esc(c.name)})

    nd.append(nodedict)

    if(children):
        for c in node.getChildren().sort_by_orderpos():
            if c.id not in written:
                written[c.id] = None
                childnodedict = buildNodeDescriptor(params, c, indent)
                nd.append(childnodedict)

    nodeattributes_dict = {}

    if attrspec == 'none':
        # no attributes should be sent
        pass
    elif attrspec == 'default_mask' or attrspec not in ['none', 'all']:
        from contenttypes.data import make_lookup_key, get_maskcache_entry
        language = params.get('lang', '')
        lookup_key = make_lookup_key(node, language=language, labels=False)
        if lookup_key not in _flask.g.mediatum.get('maskcache', {}):
            # fill cache
            node.show_node_text(labels=False, language=language)

        mask_id, field_descriptors = get_maskcache_entry(lookup_key)

        try:
            for field_descriptor in field_descriptors:
                field_attribute = field_descriptor[0]
                if field_attribute not in attrlist:
                    # attrlist may be an empty list or filled from the request parameters
                    attrlist.append(field_attribute)
        except:
            # no mask for this metadata type
            logg.exception("exception in buildNodeDescriptor, no 'nodesmall' or 'shortview' for node %s", node.id)

    elif attrspec == 'all':
        nodeattributes_dict_all_attributes = node.attributes.copy()
        if nodeattributes_dict_all_attributes:
            for k in filter(attribute_name_filter, nodeattributes_dict_all_attributes.keys()):
                nodeattributes_dict[k] = nodeattributes_dict_all_attributes[k]

    if attrlist:
        for attr in filter(attribute_name_filter, attrlist):
            if attr == "nodename":
                value = node.name
            else:
                value = node.get(attr)
            nodeattributes_dict[attr] = value

    if nodeattributes_dict:
        nodedict['attributes'] = nodeattributes_dict

    if 'files' in params:

        nodedict['files'] = []

        for file in node.getFiles():
            if file.type == "metadata" or file.type == "statistic":
                continue
            mimetype = file.mimetype
            if mimetype is None:
                mimetype = "application/x-download"
            nodedict['files'].append({'filename': esc(file.getName()), 'mime-type': mimetype, 'type': file.type})

    if 'nodename' in params:
        nodedict['name'] = node.name

    if 'nodetype' in params:
        nodedict['type'] = node.type

    if 'nodeschema' in params:
        nodedict['schema'] = node.schema
    return nd
