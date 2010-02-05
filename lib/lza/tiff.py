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

from shutil import copyfile
from utils import il16, il32, ol16, ol32, readInfo
from lza import LZAFile, LZAMetadata


class DirectoryEntry:
    def __init__(self, src="", tiff=None):
        self.tiff = tiff
        self.src = src
        self.items = []
        self.tag = 0
        self.type = 0
        self.count = 0
        self.offset = 0
        
        if len(src)==12:
            self.tag = tiff.i16(list(self.src)[0:2])
            self.type = tiff.i16(list(self.src)[2:4])
            self.count = tiff.i32(list(self.src)[4:8])
            self.offset = tiff.i32(list(self.src)[8:])

    def build(self, src):
        self.tag = 700
        self.type = 1
        self.count = len(src)
        self.offset = 0
        
    def getOutput(self, tiff):
        o = tiff.o16(1)
        o += tiff.o16(self.tag)
        o += tiff.o16(self.type)
        o += tiff.o32(self.count)
        o += tiff.o32(self.offset)
        o += tiff.o32(0)
        return o
      
        
    def getContent(self):
        content = ""
        self.tiff.src.seek(self.offset)
        content = self.tiff.src.read(self.count)
        self.tiff.src.seek(0)
        return content
        
class IFD:
    def __init__(self, tiff=None):
        self.next = 0
        self.items = []
        if tiff:
            self.items = self.build(tiff)
    
        
    def getItem(self, offset):
        for item in self.items:
            if offset==item:
                return self.items[item]
        return None

    def build(self, tiff):  
        e = {}
        entries = {}
        for i in range(1, tiff.i16(tiff.src.read(2)) + 1):
            de = DirectoryEntry(tiff.src.read(12), tiff)
            entries[de.offset] = de
        self.next = (tiff.src.tell(), tiff.i32(list(tiff.src.read(4))))
        return entries

        
class Header:
    def __init__(self, src, tiff):
        self.src = list(src)
        self.prefix = self.src[:2]      
        self.offsetIFD = tiff.i32(list(self.src[4:]))
        
    def getEndian(self):
        return "".join(self.prefix)
        
    def getOffsetIFD(self):
        return self.offsetIFD
        
class TIFFImage(LZAFile):
    def __init__(self, filename):
        self.filename = filename
        self.src = open(filename, "rb")
        self.prefix = ""
        self.ifds = []
        
        self.src.seek(0, 2)
        self.src_length = self.src.tell()
        self.src.seek(0)

        start = self.src.read(8)
        if start[:2] == "MM":
            self.i16, self.i32 = ib16, ib32
        elif start[:2] == "II":
            self.i16, self.i32 = il16, il32
            self.o16, self.o32 = ol16, ol32
        else:
            raise SyntaxError("not a TIFF IFD")
        # header
        self.header = Header(start, self)
        # ifds
        self.src.seek(self.header.getOffsetIFD()) # set position

        while 1:
            ifd = IFD(self)
            self.ifds.append(ifd) 
            if ifd.next[1]==0:
                break # last ifd found
            else:
                # set correct position for next ifd
                self.src.seek(0)
                self.src.seek(self.ifds[-1].next[1])

    
    def writeMetaData(self, data, outputfile):
        de = DirectoryEntry()
        de.build(data)
        de.offset = self.src_length + 2 + 12 + 4
       
        # write output
        self.src.seek(0)
        output = open(outputfile, "wb")
        
        old_val = 0
        for ifd in self.ifds:
            if ifd.next[1]==0:
                old_val = int(ifd.next[0])
                break
        
        output.write(self.src.read(old_val))
        output.write(self.o32(self.src_length))
        self.src.read(4) # ignore old 0000 value
        output.write(self.src.read(self.src_length - 4 - old_val))
        
        # add item
        output.write(de.getOutput(self))
        output.write(data)
        output.close()
        
    
    # extract mediatum metainformation
    def getMetaData(self):
        ifd = self.ifds[-1]
        entry = ifd.items[ifd.items.keys()[-1]]
        self.src.seek(entry.offset)
        return LZAMetadata(self.src.read(entry.count))
    
    def getOriginal(self, outputfile):
        if len(self.ifds)<2:
            raise "no lza object"
        else:
            ifd = self.ifds[-2]
            self.src.seek(0)
            output = open(outputfile, "wb")
            output.write(self.src.read(ifd.next[0]))
            self.src.read(4) # leave old id
            output.write(self.o32(0))
            output.write(self.src.read(ifd.next[1]-ifd.next[0]-4))
            output.close()


