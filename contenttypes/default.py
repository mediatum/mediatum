"""
 mediatum - a multimedia content repository

 Copyright (C) 2007 Arne Seifert <seiferta@in.tum.de>
 Copyright (C) 2007 Matthias Kramm <kramm@in.tum.de>

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
from schema.schema import loadTypesFromDB, VIEW_HIDE_EMPTY,VIEW_DATA_ONLY

class Default(tree.Node):
    def show_node_big(node, req):
        return "Unknown datatype: "+node.type

    def show_node_image(node):
        return """<img border="0" src="/img/questionmark.png">"""

    """ format preview node text """
    def show_node_text(node, words=None, language=None, seperator="<br />"):
        metatext = list()
        mask = node.getMask("nodesmall")
        if mask:
            for field in mask.getViewHTML([node], VIEW_DATA_ONLY):
                value = field[1]
                if words!=None:
                    value = highlight(value, words, '<font class="hilite">', "</font>")

                if value:
                    if field[0].startswith("author"):
                        value = '<span class="author">'+value+'</span>'
                    if field[0].startswith("subject"):
                        value = '<b>'+value+'</b>'
                    metatext.append(value)
        else:
            metatext.append('&lt;smallview mask not defined&gt;')

        return seperator.join(metatext)
    
    def can_open(node):
        return 0

    def get_name(node):
        return node.name

    def getTechnAttributes(node):
        return {}
        
    def has_object(node):
        return True
        
    def getFullView(node, language):
        masks = node.getMasks(type="fullview", language=language)
        if len(masks)>1:
            for m in masks:
                if m.getLanguage()==lang(req):
                    return m
            if not mask:
                for m in masks:
                    if m.getLanguage() in ["","no"]:
                        return m
        elif len(masks)==0:
            return tree.Node("", type="mask")
        else:
            return masks[0]


