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
from lza import LZAFile, LZAMetadata


class PDFObject:

    def __init__(self, src):
        self.src = src
        self.type = "-----"
        self.attrs = ""
        self.content = ""

        t = ""
        for i in self.src:
            if t.endswith(" obj"):
                t = ""
            elif t.endswith("stream"):
                self.type = "stream"
                t = ""

            elif t.endswith("end" + self.type):
                t = ""

            elif t.endswith(">>"):
                self.attrs = t
                t = ""

            else:
                self.content += i
            t += i

    def __str__(self):
        return self.src

    def getContent(self):
        import re
        x = re.compile(">>|endstream")
        return x.split(self.content)[1]


class Xref:

    def __init__(self, src="", doc=None):
        if src == "":
            src = "xref\r\n0 0\r\n"
        self.src = src
        self.min_id = 0
        self.max_id = 0
        self.items = []
        self.buildObj()

    def buildObj(self):
        i = 0
        for line in self.src.split("\r\n"):
            if i == 1:
                self.min_id = int(line.split(" ")[0])
                self.max_id = self.min_id + int(line.split(" ")[1])
            elif i > 1 and len(line) == 18:  # toc items
                self.items.append(line.split(" "))
            i += 1

    def getMaxObjectId(self):
        return self.max_id

    def __str__(self):
        return self.src


class Trailer:

    def __init__(self, src="", doc=None):
        self.src = src
        self.doc = doc
        self.startxref = 0
        self.attrs = []
        self.offset = 0
        self.buildObj()
        self.state = ""

    def buildObj(self):
        if self.src == "" and self.doc:
            # build empty standard trailer string
            _startxref = self.doc.src_length
            _attrs = self.doc.trailer.attrs
            if self.doc and self.doc.attr["linearized"]:
                _startxref = self.doc.trailer.startxref
                for attr in self.doc.lin_trailer.attrs:
                    if attr[0] == "Size":
                        _attrs = [("Size " + str(int(attr[1]) + 1)).split(" ")]

            self.src = "trailer\r\n"

            if len(_attrs) > 0:
                self.src += "<<"
                self.src += self.getAttributeString(_attrs)
                self.src += " /Prev " + str(self.doc.trailer.startxref)
                self.src += ">>\r\n"
            self.src += "startxref\r\n" + str(_startxref) + "\r\n%%EOF"

        l = ""
        for i in self.src.replace(" ", "").replace("\r", "").replace("\n", ""):
            if l.endswith("startxref"):
                l = ""
            if l.endswith("%"):
                self.startxref = int(l[:-1])
                break
            l += i
        l = ""
        for i in self.src.replace("\r", "").replace("\n", ""):
            if l.endswith("<<"):
                l = ""
            if l.endswith(">>"):
                l = l[:-2]
                for item in l.split("/"):
                    if str(item.strip()) != "":
                        self.attrs.append(item.strip().split(" "))
                break
            l += i

    def setAttribute(self, name, value):
        self.state = "upd"
        for i, attr in enumerate(self.attrs):
            if attr[0] == name:
                attr = [attr[0]]
                attr.extend(str(value).split(" "))
                self.attrs[i] = attr
                break

    def getAttribute(self, name):
        for attr in self.attrs:
            if attr[0] == name:
                return " ".join(attr[1:])
        return ""

    def getAttributeString(self, attrs=None):
        ret = ""
        if attrs:
            att = attrs
        else:
            att = self.attrs

        for attr in att:
            ret += " /" + " ".join(attr)
        return ret

    def __str__(self):
        if self.state == "upd":
            self.src = "trailer\r\n"
            if len(self.attrs) > 0:
                self.src += "<<" + self.getAttributeString(self.attrs) + ">>\r\n"
            self.src += "startxref\r\n" + str(self.startxref) + "\r\n%%EOF"
        return self.src

    def __len__(self):
        return len(self.src)


class PDFDocument(LZAFile):

    def __init__(self, filename):
        self.filename = filename
        self.src = open(filename, "rb")
        self.attr = {}
        # normal trailer, xref
        self.trailer = None
        self.xref = None
        # trailer, xref for linearized files
        self.lin_trailer = None
        self.lin_xref = None

        self.src.seek(-500, 2)

        t = self.src.read(500)
        self.src_length = self.src.tell()
        t = Trailer(t[t.rfind("trailer"):])
        t.offset = self.src_length - len(t)

        self.trailer = t
        self.src.seek(0)
        self.src.seek(t.startxref, 1)

        l = ""
        while not l.endswith("trailer"):
            l += self.src.read(1)
        self.src.seek(0)

        xref = Xref(l[:-7])
        self.xref = xref

        if "Linearized" in self.src.read(500):  # last position for linearized option
            self.attr["linearized"] = True
            self.getLinearizedTrailer()
        else:
            self.attr["linearized"] = False
        self.src.seek(0)

    def filetype(self):
        return "PDF-Document"

    def getLinearizedTrailer(self):
        print "build linearized xref and trailer"

        self.src.seek(0)
        self.src.seek(self.trailer.startxref, 1)
        t = ""
        while not t.endswith("%%EOF"):
            if t.endswith("trailer"):
                self.lin_xref = Xref(t[:-7])
                t = "trailer"

            t += self.src.read(1)
        self.lin_trailer = Trailer(t)
        self.src.seek(0)

    def getLinearizedXref(self):
        self.src.seek(self.src_length)
        i = 0
        t = ""
        while 1:
            self.src.seek(i, 2)
            t = self.src.read(1) + t
            i -= 1
            if t.startswith("xref"):
                self.src.seek(i, 2)
                if self.src.read(1) != "t":
                    break
        return Xref(t[:t.find("trailer")])

    def writeMetaData(self, data, outputfile="out.pdf"):
        _maxid = self.xref.max_id
        if self.attr["linearized"]:
            _maxid = self.lin_xref.max_id + 1
        _s = str(_maxid) + " 0 obj\r\n"
        _s += "stream\r\n<< /Type /Metadata/ Subtype /XML /Length " + str(len(data)) + ">>\r\n" + data + "\r\n"
        _s += "endstream\r\nendobj\r\n"

        copyfile(self.filename, outputfile)
        output = open(outputfile, "ab")
        output.write("\r\n" + _s)

        if data != "":
            # build special object
            if self.attr["linearized"]:
                _xref = "xref\r\n" + str(self.lin_xref.max_id + 1) + " 1\r\n"
            else:
                _xref = "xref\r\n" + str(self.xref.max_id) + " 1\r\n"
            _xref += str(self.src_length + 2).rjust(10, "0") + " 00000 n\r\n"
            _xref = Xref(_xref)
        output.write(str(_xref))
        self.src_length = self.src_length + 2 + len(_s)

        if _s != "":
            _trailer = Trailer("", self)
            _trailer.setAttribute("Size", int(_trailer.getAttribute("Size")) + 1)  # update trailer Size attribute

        output.write(str(_trailer))
        output.close()

    def getObject(self, offset):
        ret = ""
        self.src.seek(int(offset))
        while not ret.endswith("endobj"):
            ret += self.src.read(1)
        return PDFObject(ret)

    def getMetaData(self):
        xref = None
        if self.attr["linearized"]:
            # get last xref written by lza
            xref = self.getLinearizedXref()
        else:
            xref = self.xref

        i = xref.items[len(xref.items) - 1][0]
        while i[0] == "0":
            i = i[1:]
        obj = self.getObject(int(i))
        return LZAMetadata(obj.getContent())

    def getOriginal(self, outputfile):
        if self.getMetaData().lzaData():
            offset = self.src_length
            if self.attr["linearized"]:
                offset = self.getLinearizedXref().items[0][0]
            else:
                offset = self.xref.items[0][0]

            while offset.startswith("0"):
                offset = offset[1:]

            input = open(self.filename, "rb")
            output = open(outputfile, "wb")
            output.write(input.read(int(offset) - 2))  # remove newline added while writing mediatum data
            output.close()
            input.close()
        else:
            raise "no lza object"
