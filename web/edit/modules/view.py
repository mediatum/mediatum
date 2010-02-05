"""
 mediatum - a multimedia content repository

 Copyright (C) 2009 Arne Seifert <seiferta@in.tum.de>

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

import core.tree as tree
from utils.utils import getFormatedString

def getContent(req, ids):
    ret = ""
    
    if len(ids)>=0:
        ids = ids[0]

    node = tree.getNode(ids)

    if hasattr(node, "show_node_big"):
        ret += req.getTALstr('<span i18n:translate="edit_tabarea_msg1"/><br><b i18n:translate="hint"></b><span i18n:translate="edit_tabarea_msg2"/><br/><hr/>',{})
        ret += getFormatedString(node.show_node_big(req))  
    else:
        ret += req.getTALstr('<p class="error" style="text-align:center" i18n:translate="" tal:content="edit_object_not_viewable">TEXT</p>',{})
    
    return ret