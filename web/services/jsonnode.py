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

import sys

if sys.version[0:3] < '2.6':
    import simplejson as json
else:
    import json

from utils.utils import esc, u, u2

def buildNodeDescriptor(req, node, indent=None, written=None, children=True, children_access=None, parents=False,):
    nd =[]
    d = {}
    if written is None:
        written = {}
    
    nodedict = {}
    nodedict['id'] = node.id
    nodedict['name'] = node.name
    
    if node.type is None:
        nodedict['type'] = 'node'
    else:
        nodedict['type'] = node.type    
        
    if node.read_access:
        nodedict['read'] = esc(node.read_access)
    if node.write_access:
        nodedict['write'] = esc(node.write_access)
    if node.data_access:
        nodedict['data'] = esc(node.data_access) 
        
    nodeattributes_dict = node.attributes
    
    for k in nodeattributes_dict.keys():
        nodeattributes_dict[k] = u2((nodeattributes_dict[k]))
                
    nodedict['attributes'] = nodeattributes_dict
    
    try:
        nodedict['defaultexport'] = node.show_node_text(labels=1,language=req.params.get('lang', ''))
    except:
        nodedict['defaultexport'] = []    
    
    nodedict['files'] = []
    
    for file in node.getFiles():
        if file.type == "metadata" or file.type == "statistic":
            continue
        mimetype = file.mimetype
        if mimetype is None:
            mimetype = "application/x-download"
        nodedict['files'].append({'filename':esc(file.getName()), 'mime-type': mimetype, 'type': file.type})

    if children:
        nodedict['children'] = []
        for c in node.getChildren().sort():
            if (not children_access) or (children_access and children_access.hasAccess(c, 'read')):
                nodedict['children'].append({'id': str(c.id), 'type': c.type, 'name': esc(c.name)})
                
    if parents:
        nodedict['parents'] = []
        for c in node.getParents().sort():
            if (not children_access) or (children_access and children_access.hasAccess(c, 'read')):
                nodedict['parents'].append({'id': str(c.id), 'type': c.type, 'name': esc(c.name)}) 
                
    nd.append(nodedict)
                
    if(children):
        for c in node.getChildren().sort():
            if (not children_access) or (children_access and children_access.hasAccess(c, 'read')):
                if c.id not in written:
                    written[c.id] = None
                    childnodedict = buildNodeDescriptor(c, indent, children_access=children_access)
                    nd.append(childnodedict)                                
    return nd
    
def getSingleNodeJSON(node, children=False):
    nd = buildNodeDescriptor(node,children=children)
    return json.dumps(nd, indent=4) 
