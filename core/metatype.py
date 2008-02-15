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

class Context:

    def __init__(self, field, value="", width=400, name="", lock=0, language=None, collection=None, user=None, ip=""):
        self.field = field
        self.value=value
        self.width = width
        self.name = name
        self.language = language
        self.collection = collection
        self.ip = ip
        self.user = user
        self.access = acl.AccessData(user=user)
        self.lock = lock

        
class Metatype:

    def getEditorHTML(self, field, value="", width=400, name="", lock=0, language=None):
        return ""

    def getSearchHTML(self, context):
        None

    def getFormatedValue(self, field, node, language=None):
        None

    def getFormatedValueForDB(self, field, value, language=None):
        return value

    def getMaskEditorHTML(self, value="", metadatatype=None, language=None):
        return ""

    def isContainer(self):
        return False

    def getName(self):
        return ""
        
    ''' events '''
    def event_metafield_changed(self, node, field):
        None

