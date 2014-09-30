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

from utils import il16, il32, ib16, ib32, ol16, ol32, reverse, readInfo
from lza import LZAFile, LZAMetadata


MARKER = {
    0xFFC0: ("SOF0", "Baseline DCT"),
    0xFFC1: ("SOF1", "Extended Sequential DCT"),
    0xFFC2: ("SOF2", "Progressive DCT"),
    0xFFC3: ("SOF3", "Spatial lossless"),
    0xFFC4: ("DHT", "Define Huffman table"),
    0xFFC5: ("SOF5", "Differential sequential DCT"),
    0xFFC6: ("SOF6", "Differential progressive DCT"),
    0xFFC7: ("SOF7", "Differential spatial"),
    0xFFC8: ("JPG", "Extension"),
    0xFFC9: ("SOF9", "Extended sequential DCT (AC)"),
    0xFFCA: ("SOF10", "Progressive DCT (AC)"),
    0xFFCB: ("SOF11", "Spatial lossless DCT (AC)"),
    0xFFCC: ("DAC", "Define arithmetic coding conditioning"),
    0xFFCD: ("SOF13", "Differential sequential DCT (AC)"),
    0xFFCE: ("SOF14", "Differential progressive DCT (AC)"),
    0xFFCF: ("SOF15", "Differential spatial (AC)"),
    0xFFD0: ("RST0", "Restart 0"),
    0xFFD1: ("RST1", "Restart 1"),
    0xFFD2: ("RST2", "Restart 2"),
    0xFFD3: ("RST3", "Restart 3"),
    0xFFD4: ("RST4", "Restart 4"),
    0xFFD5: ("RST5", "Restart 5"),
    0xFFD6: ("RST6", "Restart 6"),
    0xFFD7: ("RST7", "Restart 7"),
    0xFFD8: ("SOI", "Start of image"),
    0xFFD9: ("EOI", "End of image"),
    0xFFDA: ("SOS", "Start of scan"),
    0xFFDB: ("DQT", "Define quantization table"),
    0xFFDC: ("DNL", "Define number of lines"),
    0xFFDD: ("DRI", "Define restart interval"),
    0xFFDE: ("DHP", "Define hierarchical progression"),
    0xFFDF: ("EXP", "Expand reference component"),
    0xFFE0: ("APP0", "Application segment 0"),
    0xFFE1: ("APP1", "Application segment 1"),
    0xFFE2: ("APP2", "Application segment 2"),
    0xFFE3: ("APP3", "Application segment 3"),
    0xFFE4: ("APP4", "Application segment 4"),
    0xFFE5: ("APP5", "Application segment 5"),
    0xFFE6: ("APP6", "Application segment 6"),
    0xFFE7: ("APP7", "Application segment 7"),
    0xFFE8: ("APP8", "Application segment 8"),
    0xFFE9: ("APP9", "Application segment 9"),
    0xFFEA: ("APP10", "Application segment 10"),
    0xFFEB: ("APP11", "Application segment 11"),
    0xFFEC: ("APP12", "Application segment 12"),
    0xFFED: ("APP13", "Application segment 13"),
    0xFFEE: ("APP14", "Application segment 14"),
    0xFFEF: ("APP15", "Application segment 15"),
    0xFFF0: ("JPG0", "Extension 0"),
    0xFFF1: ("JPG1", "Extension 1"),
    0xFFF2: ("JPG2", "Extension 2"),
    0xFFF3: ("JPG3", "Extension 3"),
    0xFFF4: ("JPG4", "Extension 4"),
    0xFFF5: ("JPG5", "Extension 5"),
    0xFFF6: ("JPG6", "Extension 6"),
    0xFFF7: ("JPG7", "Extension 7"),
    0xFFF8: ("JPG8", "Extension 8"),
    0xFFF9: ("JPG9", "Extension 9"),
    0xFFFA: ("JPG10", "Extension 10"),
    0xFFFB: ("JPG11", "Extension 11"),
    0xFFFC: ("JPG12", "Extension 12"),
    0xFFFD: ("JPG13", "Extension 13"),
    0xFFFE: ("COM", "Comment")
}


class JPEGImage(LZAFile):

    def __init__(self, filename):
        self.filename = filename
        self.items = []
        self.com = 0
        self.src = open(filename, "rb")

        self.src.seek(0, 2)
        self.src_length = self.src.tell()
        self.src.seek(0)

        s = " "
        while 1:

            if s and ord(s) == 255:
                s = s + self.src.read(1)
                x = ib16(s)

                if MARKER.has_key(x):
                    self.items.append((self.src.tell() - 2, MARKER[x][0]))

            s = self.src.read(1)
            if self.src.tell() == self.src_length:
                break
        self.src.close()

    # extract mediatum metainformation
    def getMetaData(self):
        ret = ""

        index = -1
        for item in self.items:
            if item[1] == "SOF0":
                index = self.items.index(item)

        if index < 0:
            return LZAMetadata("")

        if self.src.closed:
            self.src = open(self.filename, "rb")

        if self.items[index - 1][1] == "COM":
            self.src.seek(self.items[index - 1][0] + 4)  # marker + length
            return LZAMetadata(self.src.read(self.items[index][0] - self.src.tell()))

    def writeMetaData(self, data, outputfile):
        index = -1

        for item in self.items:
            if item[1] == "SOF0":
                index = self.items.index(item)
        if index < 0:
            raise SyntaxError("wrong filetype")

        if self.items[index - 1][1] == "COM":
            # update value
            _end = self.items[index - 1][0]
            print "update comment"
            input = open(self.filename, "rb")
            input.seek(self.items[index - 1][0] + 4)
            data = LZAMetadata(data)
            data.addOriginal(input.read(self.items[index][0] - self.items[index - 1][0] - 4))
            input.close()

        else:
            # insert value
            _end = self.items[index][0]

        input = open(self.filename, "rb")
        output = open(outputfile, "wb")
        output.write(input.read(_end))

        output.write("\xFF\xFE")
        output.write(reverse(ol16(len(str(data)))))

        output.write(str(data))
        input.seek(self.items[index][0])

        output.write(input.read(self.src_length - input.tell()))
        input.close()
        output.close()

    def getOriginal(self, outputfile=""):

        orig = self.getMetaData().GetOriginal()
        input = open(self.filename, "rb")
        input.seek(0, 2)
        input_length = input.tell()
        input.seek(0)
        print input.tell()

        com_start = input_length
        output = open(outputfile, "wb")

        for item in self.items:
            if item[1] == "COM":
                com_start = item[0]
                index = self.items.index(item)
                com_end = self.items[index + 1][0]
                input.seek(0)
                break

        # write until old comment
        output.write(input.read(com_start))
        if len(orig) > 0:
            output.write("\xFF\xFE")
            output.write(reverse(ol16(len(orig))))
            output.write(orig)
        input.seek(com_end)
        # write file footer
        while input.tell() < input_length:
            output.write(input.read(1))
        output.close()
        input.close()
