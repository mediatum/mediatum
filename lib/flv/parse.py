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

from struct import unpack
from datetime import datetime

class FLVReader(dict):
    # Tag types
    AUDIO = 8
    VIDEO = 9
    META = 18
    UNDEFINED = 0

    def __init__(self, filename):
        """
        Pass the filename of an flv file and it will return a dictionary of meta
        data.
        """
        self.file = open(filename, 'rb')
        self.signature = self.file.read(3)
        assert self.signature == 'FLV', 'Not an flv file'
        self.version = self.readbyte()
        self.typeFlags = self.readbyte()
        self.dataOffset = self.readint()
        extraDataLen = self.dataOffset - self.file.tell()
        self.extraData = self.file.read(extraDataLen)
        try:
            self.readtag()
        except:
            print "dirty file"
            dimension = getFLVSize(filename)
            self.update({"width":dimension[0], "height":dimension[1]})
            

    def readtag(self):
        unknown = self.readint()
        tagType = self.readbyte()
        dataSize = self.read24bit()
        timeStamp = self.read24bit()
        unknown = self.readint()
        if tagType == self.AUDIO:
            print "Can't handle audio tags yet"
        elif tagType == self.VIDEO:
            print "Can't handle video tags yet"
        elif tagType == self.META:
            endpos = self.file.tell() + dataSize
            event = self.readAMFData()
            metaData = self.readAMFData()
            self.update(metaData)
        elif tagType == self.UNDEFINED:
            print "Can't handle undefined tags yet"

    def readint(self):
      data = self.file.read(4)
      return unpack('>I', data)[0]

    def readshort(self):
      data = self.file.read(2)
      return unpack('>H', data)[0]

    def readbyte(self):
      data = self.file.read(1)
      return unpack('B', data)[0]

    def read24bit(self):
      b1, b2, b3 = unpack('3B', self.file.read(3))
      return (b1 << 16) + (b2 << 8) + b3

    def readAMFData(self, dataType=None):
        if dataType is None:
            dataType = self.readbyte()
        funcs = {
            0: self.readAMFDouble,
            1: self.readAMFBoolean,
            2: self.readAMFString,
            3: self.readAMFObject,
            8: self.readAMFMixedArray,
           10: self.readAMFArray,
           11: self.readAMFDate
        }
        func = funcs[dataType]
        if callable(func):
            return func()

    def readAMFDouble(self):
        return unpack('>d', self.file.read(8))[0]

    def readAMFBoolean(self):
        return self.readbyte() == 1

    def readAMFString(self):
        size = self.readshort()
        return self.file.read(size)

    def readAMFObject(self):
        data = self.readAMFMixedArray()
        result = object()
        result.__dict__.update(data)
        return result

    def readAMFMixedArray(self):
        size = self.readint()
        result = {}
        for i in range(size):
            key = self.readAMFString()
            dataType = self.readbyte()
            if not key and dataType == 9:
                break
            result[key] = self.readAMFData(dataType)
        return result

    def readAMFArray(self):
        size = self.readint()
        result = []
        for i in range(size):
            result.append(self.readAMFData)
        return result

    def readAMFDate(self):
        return datetime.fromtimestamp(self.readAMFDouble())

def readU32(fi):
    s = fi.read(4)
    l = ord(s[0])<<24 | ord(s[1])<<16 | ord(s[2])<<8 | ord(s[3])<<0
    return l
def readU24(fi):
    s = fi.read(3)
    l = ord(s[0])<<16 | ord(s[1])<<8 | ord(s[2])<<0
    return l
def readU16(fi):
    s = fi.read(2)
    l = ord(s[0])<<8 | ord(s[1])<<0
    return l
def readU8(fi):
    return ord(fi.read(1))

class BitReader:
    def __init__(self,file):
        self.file = file
        self.bitpos = 0
        self.byte = 0
    def getbit(self):
        if not self.bitpos:
            self.byte = readU8(self.file)
            self.bitpos = 8
        self.bitpos = self.bitpos - 1 
        return (self.byte >> self.bitpos)&1
    def getbits(self, n): 
        x = 0
        for i in range(n):
            x = (x<<1) | self.getbit()
        return x


CODECS={2:"Sorenson H.263", 3:"Screen Video", 4:"On2 VP6", 5:"On2 VP6 w/ alpha channel", 6:"Screen Video V2"}

def getFLVSize(filename):
    fi = open(filename, "rb")
    head = fi.read(3)
    if head != "FLV":
        raise AttributeError("Not an FLV file")
    version = fi.read(1)
    flags = fi.read(1)
    length = readU32(fi)
    fi.read(length - 9)
    prevsize = 0
    for i in range(10):
        prevlen = readU32(fi)
        if prevlen and prevlen != prevsize:
            raise AttributeError("Error in FLV file")
        type = readU8(fi)
        size = readU24(fi)
        prevsize = size+11
        if type == 8: # audio data
            fi.read(7+size)
        elif type == 18: # script data
            fi.read(7+size)
        elif type == 9:
            fi.read(7)
            flags = readU8(fi)
            codec = flags & 15
            keyframe = flags >> 4
            
            if codec == 2 or keyframe>=5: #h.263
                bitread = BitReader(fi)
                l = bitread.getbits(17)
                if l != 1:
                    raise AttributeError("Invalid h.263 start code")
                version = bitread.getbits(5)
                tempo = bitread.getbits(8)
                picsize = bitread.getbits(3)
                if picsize == 0:
                    width = bitread.getbits(8)
                    height = bitread.getbits(8)
                    return width,height
                elif picsize == 1:
                    width = bitread.getbits(16)
                    height = bitread.getbits(16)
                    return width,height
                elif picsize == 2:
                    return 352,288
                elif picsize == 3:
                    return 176,144
                elif picsize == 4:
                    return 128,96
                elif picsize == 5:
                    return 320,240
                elif picsize == 6:
                    return 160,120
                else:
                    raise AttributeError("Invalid h.263 picture size")
            elif codec == 3 or codec == 6: #screen video
                width = readU16(fi)>>4
                height = readU16(fi)>>4
                return width,height
            elif codec == 4 or codec == 5: #on2 vp6 video
                keyframe = readU8(fi)
                if keyframe&0x80:
                    #raise AttributeError("On2 VP6 Video doesn't start with a key frame")
                    pass
                version = readU8(fi)
                if keyframe&1:
                    fi.read(2)
                rows_coded = readU8(fi)
                cols_coded = readU8(fi)
                rows_displayed = readU8(fi)
                cols_displayed = readU8(fi)
                print rows_displayed, cols_displayed
                
                return rows_displayed*16,cols_displayed*16
            else:
                raise AttributeError("Codec "+CODECS.get(codec,str(codec))+" not supported")
        else:
            fi.read(7+size)
            

if __name__ == "__main__":
    #print getFLVSize("/home/data/videos/testvideo.flv")
    #print getFLVSize("/home/data/videos/Abiotv-carForWomen895.flv")
    print getFLVSize("tzanou.flv")


