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

import core.acl as acl
from core.translation import t, lang
from core.acl import AccessData
from contenttypes import data
from schema.schema import VIEW_HIDE_EMPTY
from contenttypes.data import ContentType
from core.transition.postgres import check_type_arg_with_schema


""" flash class """

@check_type_arg_with_schema
class Flash(ContentType):

    def getTypeAlias(self):
        return "flash"

    def getCategoryName(self):
        return "video"

    def _prepareData(self, req, words=""):
        access = acl.AccessData(req)
        mask = self.getFullView(lang(req))
        obj = {'deleted': False, 'access': access}
        node = self
        if self.get('deleted') == 'true':
            node = self.getActiveVersion()
            obj['deleted'] = True
        if mask:
            obj['metadata'] = mask.getViewHTML([node], VIEW_HIDE_EMPTY, lang(req), mask=mask)  # hide empty elements
        else:
            obj['metadata'] = []
        obj['node'] = node
        obj['path'] = req.params.get("path", "")
        return obj

    """ format big view with standard template """
    def show_node_big(self, req, template="contenttypes/flash.html", macro="showbig"):
        return req.getTAL(template, self._prepareData(req), macro)

    """ returns preview image """
    def show_node_image(self):
        return '<img src="/thumbs/' + self.id + '" class="thumbnail" border="0"/>'

    def isContainer(self):
        return 0

    def getSysFiles(self):
        return []

    def getLabel(self):
        return self.name

    """ list with technical attributes for type flash """
    def getTechnAttributes(self):
        return {"Standard": {"creationtime": "Erstelldatum",
                             "creator": "Ersteller"}}

    """ popup window for actual nodetype """
    def popup_fullsize(self, req):
        access = AccessData(req)
        if not access.hasAccess(self, "data") or not access.hasAccess(self, "read"):
            req.write(t(req, "permission_denied"))
            return

        f = ""
        for filenode in self.getFiles():
            if filenode.getType() in ("original", "video"):
                f = u"/file/{}/{}".format(self.id,
                                          filenode.getName())
                break
        req.writeTAL("contenttypes/flash.html", {"path": f}, macro="fullsize")

    def popup_thumbbig(self, req):
        self.popup_fullsize(req)

    def getEditMenuTabs(self):
        return "menulayout(view);menumetadata(metadata;files;lza);menuclasses(classes);menusecurity(acls)"

    def getDefaultEditTab(self):
        return "view"
