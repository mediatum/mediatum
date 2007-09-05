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

class Default(tree.Node):
    def show_node_big(node, req):
        return "Unknown datatype: "+node.type

    def show_node_image(node):
        return """<img border="0" src="/img/questionmark.png">"""

    def show_node_text(node, words=None):
        return """<p class=\"descbox\"><b>Name:</b> "+node.name+"<br></p>""";
       
    def can_open(node):
        return 0

    def get_name(node):
        return node.name

    def getTechnAttributes(node):
        return {}

