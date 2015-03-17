"""
 mediatum - a multimedia content repository

 Copyright (C) 2010 Arne Seifert <seiferta@in.tum.de>

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

from core import Node

from utils.utils import mkKey


class ShoppingBag(Node):

    def getItems(self):
        return self.get("items").split(";")

    def setItems(self, items=[]):
        self.set("items", ";".join(items))

    def isShared(self):
        if self.get("key") != "":
            return 1
        return 0

    def getSharedKey(self):
        return self.get("key")

    def createShareKey(self):
        k = mkKey()
        self.set("key", k)
        return k

    def stopShare(self):
        self.removeAttribute("key")

    def isContainer(self):
        return False
