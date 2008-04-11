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

from core.acl import AccessData
import re
import os
import core.athana as athana
import default

SRC_PATTERN = re.compile('src="([^":/]*)"')

""" these are not TAL templates, but a much more simplified version. All that
    is replaced are images and links to ${next} """
def includetemplate(node, file, substitute):
    ret = ""
    if os.path.isfile(file):
        
        fi = open(file, "rb")
        s = str(fi.read())

        for string,replacement in substitute.items():
            s = s.replace(string, replacement)
       
        lastend = 0
        scanner = SRC_PATTERN.scanner(s)
        while 1:
            match = scanner.search()
            if match is None:
                ret += s[lastend:]
                break
            else:
                ret += s[lastend:match.start()]
                imgname = match.group(1)
                ret += 'src="/file/'+node.id+'/'+imgname+'"'
                lastend = match.end()
        fi.close()
        
    else:
        print "Couldn't find",file
    return ret

""" directory class """
class Directory(default.Default):

    """ format big view with standard template """
    def show_node_big(node, req):
        content = ""
        link = "node?id="+node.id + "&amp;files=1"
        
        for f in node.getFiles():
            if f.type=="content" and f.mimetype=="text/html":
                content = includetemplate(node, f.retrieveFile(), {'${next}': link})
        return content
    
    """ format node image with standard template """
    def show_node_image(node,language=None):
        return athana.getTAL("contenttypes/directory.html", {"node":node}, macro="thumbnail",language=language)
     
    def can_open(node):
        return 1

    def getLabel(node):
        label = node.get("label")
        if not label:
            label = node.getName()
        return label

    """ list with technical attributes for type directory """
    def getTechnAttributes(node):
        return {}

    def getLogoPath(node):
        for file in node.getFiles():
            if file.getType()=='image':
                return "/file/"+str(node.id)+"/"+file.getName()
        return ""
