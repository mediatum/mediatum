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
#from utils import *
from core.tree import nodeclasses


class Datatype:

    def __init__(self, id, name, classname, comment=""):
        self.id = id                # autoincrement number
        self.name = name            # name = filename of file in /objtypes
        self.classname = classname  # objectclassname in file
        self.comment = comment      # will be used for dropdown-boxes

    def getId(self):
        return self.id

    def getName(self):
        return self.name

    def getClassname(self):
        return self.classname

    def getComment(self):
        return self.comment

    def getLongName(self):
        return self.classname

    def isSystemType(self):
        return 0


def loadAllDatatypes():
    datalist = []
    for key, cls in nodeclasses.items():
        datalist += [Datatype(key, key, cls.__name__, cls.__module__ + '.' + cls.__name__)]
    return datalist


def loadNonSystemTypes():
    dlist = []
    for key, cls in nodeclasses.items():
        n = cls(name='n', type=key)
        if key not in ["default", "root", "home"] and hasattr(n, "isSystemType") and n.isSystemType() == 0:
            dlist += [Datatype(key, key, cls.__name__, cls.__module__ + '.' + cls.__name__)]
    return dlist
