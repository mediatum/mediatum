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

import xml.parsers.expat

def u(s):
    try:
        return s.encode("utf-8")
    except:
        try:
            return s.decode("latin-1").encode("utf-8")
        except:
            return s

def ib16(c,o=0):
    return ord(c[o+1]) + (ord(c[o])<<8)
def ib32(c,o=0):
    return ord(c[o+3]) + (ord(c[o+2])<<8) + (ord(c[o+1])<<16) + (ord(c[o])<<24)

def il16(c,o=0):
    return ord(c[o]) + (ord(c[o+1])<<8)
def il32(c,o=0):
    return ord(c[o]) + (ord(c[o+1])<<8) + (ord(c[o+2])<<16) + (ord(c[o+3])<<24)
    
def ol16(i):
    return chr(i&255) + chr(i>>8&255)
    
def ol32(i):
    return chr(i&255) + chr(i>>8&255) + chr(i>>16&255) + chr(i>>24&255)

  
reverse = lambda txt: txt[::-1]


def readInfo():
    file = open("rdf.xml", "rb")
    s = ""
    while 1:
        line = file.readline()
        if not line:
            break
        s+= line    
            
    return s
    
    
    
def buildObjects(s):
    
    def start_element(name, attrs):
        print 'Start element:', name, attrs
    def end_element(name):
        print 'End element:', name
    def char_data(data):
        print 'Character data:', repr(data)


    p = xml.parsers.expat.ParserCreate()

    p.StartElementHandler = start_element
    p.EndElementHandler = end_element
    p.CharacterDataHandler = char_data

    p.Parse(s, 1)
