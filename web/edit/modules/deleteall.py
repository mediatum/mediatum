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

import mediatumtal.tal as _tal
import web.edit.edit_common as _web_edit_edit_common

def getContent(req, ids):
    show_dir_nav = _web_edit_edit_common.ShowDirNav(req)
    return _tal.processTAL({'ids': ",".join(show_dir_nav.get_ids_from_req())},
            file="web/edit/modules/deleteall.html",
            macro="view_node",
            request=req,
           )
