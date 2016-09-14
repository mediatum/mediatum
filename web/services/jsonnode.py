"""
 mediatum - a multimedia content repository

 Copyright (C) 2007 Arne Seifert <seiferta@in.tum.de>
 Copyright (C) 2007 Matthias Kramm <kramm@in.tum.de>
 Copyright (C) 2011 Werner F. Neudenberger <neudenberger@ub.tum.de>

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
import json
import logging

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
        # except:
        #    logg.error('Error: web.services.jsonnode: could not get default mask content')
        #    nodedict['defaultexport'] = []

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
        from core.transition.globals import request
        language = params.get('lang', '')
        lookup_key = make_lookup_key(node, language=language, labels=False)
        if 'maskcache' not in request.app_cache or lookup_key not in request.app_cache['maskcache']:
            # fill cache
            node.show_node_text(labels=False, language=language)

        mask_id, field_descriptors = get_maskcache_entry(lookup_key, request.app_cache['maskcache'], request.app_cache['maskcache_accesscount'])

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

