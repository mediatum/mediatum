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

from utils.utils import esc, u2
from schema.schema import getMetaType
from web.services.serviceutils import attribute_name_filter


logg = logging.getLogger(__name__)


def buildNodeDescriptor(req, node, indent=None, written=None, children=True, children_access=None, parents=False):
    nd = []
    d = {}
    if written is None:
        written = {}

    nodedict = {}
    nodedict['id'] = node.id

    mask = req.params.get('mask', 'none').lower()

    attrlist = req.params.get('attrlist', [])
    if attrlist:
        attrlist = attrlist.split(',')

    attrspec = req.params.get('attrspec', 'default_mask')
    # 'all': no restriction, send all attributes
    # 'none': to not send any attribute at all
    # 'default_mask' (default): only send attributes that correspond to the default mask fields
    #
    # remark: attributes specified comma separated in 'attrlist' are added to those specified by 'attrspec'
    #

    if mask == 'default':
        maskcachetype = req.params.get('maskcache', 'deep')  # 'deep', 'shallow', 'none'
        nodedict['defaultexport'] = node.show_node_text(labels=1, language=req.params.get('lang', ''), cachetype=maskcachetype)
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
        except:
            nodedict['defaultexport'] = "error"

    if children:
        nodedict['children'] = []
        for c in node.getChildren().sort_by_orderpos():
            if (not children_access) or (children_access and children_access.hasAccess(c, 'read')):
                nodedict['children'].append({'id': ustr(c.id), 'type': c.type, 'name': esc(c.name)})

    if parents:
        nodedict['parents'] = []
        for c in node.getParents().sort_by_orderpos():
            if (not children_access) or (children_access and children_access.hasAccess(c, 'read')):
                nodedict['parents'].append({'id': ustr(c.id), 'type': c.type, 'name': esc(c.name)})

    nd.append(nodedict)

    if(children):
        for c in node.getChildren().sort_by_orderpos():
            if (not children_access) or (children_access and children_access.hasAccess(c, 'read')):
                if c.id not in written:
                    written[c.id] = None
                    childnodedict = buildNodeDescriptor(req, c, indent, children_access=children_access)
                    nd.append(childnodedict)

    # if node.read_access:
    #    nodedict['read'] = esc(node.read_access)
    # if node.write_access:
    #    nodedict['write'] = esc(node.write_access)
    # if node.data_access:
    #    nodedict['data'] = esc(node.data_access)

    nodeattributes_dict = {}

    if attrspec == 'none':
        # no attributes should be sent
        pass
    elif attrspec == 'default_mask' or attrspec not in ['none', 'all']:
        from contenttypes.default import make_lookup_key, get_maskcache_entry, maskcache
        language = req.params.get('lang', '')
        lookup_key = make_lookup_key(node, language=language, labels=False)
        if lookup_key not in maskcache:
            # fill cache
            node.show_node_text(labels=False, language=language, cachetype='deep')

        field_descriptors = get_maskcache_entry(lookup_key)

        try:
            mask = field_descriptors[0]
            for field_descriptor in field_descriptors[1:]:
                field_attribute = field_descriptor[0]
                #fd = field_descriptor[1]
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
                nodeattributes_dict[k] = u2((nodeattributes_dict_all_attributes[k]))

    if attrlist:
        for attr in filter(attribute_name_filter, attrlist):
            nodeattributes_dict[attr] = u2(node.get(attr))

    if nodeattributes_dict:
        nodedict['attributes'] = nodeattributes_dict

    if 'files' in req.params:

        nodedict['files'] = []

        for file in node.getFiles():
            if file.type == "metadata" or file.type == "statistic":
                continue
            mimetype = file.mimetype
            if mimetype is None:
                mimetype = "application/x-download"
            nodedict['files'].append({'filename': esc(file.getName()), 'mime-type': mimetype, 'type': file.type})

    if 'nodename' in req.params:
        nodedict['name'] = node.name

    if 'nodetype' in req.params:
        if node.type is None:
            nodedict['type'] = 'node'
        else:
            nodedict['type'] = node.type
    return nd


def getSingleNodeJSON(req, node, children=False):
    nd = buildNodeDescriptor(req, node, children=children)
    return json.dumps(nd, indent=4)
