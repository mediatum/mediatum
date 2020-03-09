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

from contenttypes import Data as _Data
from core import db as _db

_q = _db.query

def getContent(req, ids):

    _node = _q(_Data).get(long(ids[0]))

    return _tal.processTAL({'id': _node.id, 'action': 'move'}, file="web/edit/modules/movecopyobject.html", macro="view_node", request=req)
