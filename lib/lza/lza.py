import xml.parsers.expat
from utils import buildObjects, u

class LZAFile:

    def __init__(self):
        None
        
    def filetype(self):
        raise "not implemented"
    
    # writes metadata into file
    def writeMetaData(self, data, outputfile):
        raise "not implemented"
    
    # delivers metadata object
    def getMetaData(self):
        raise "not implemented"
        
    # delivers original file objeect
    def getOriginal(self, outputfile=""):
        raise "not implemented"

        
    
class MetadataItem:
    def __init__(self, name="", path=[], value="", attr={}):
        self.name = name
        self.path = list(path)
        self.attr = attr
        self.value = value.strip()
        self.children = []
    
    def addChild(self, child):
        self.children.append(child)
        
class LZAMetadata:

    def __init__(self, s=""):
        self.items = None   
        self.id = {}
        self.src = s

        t = ""
        id = ""
        found = False
        for i in self.src:
            
            if t.endswith('<?xpacket '):
                 found = True
            t+=i
            
            if t.endswith('?>'):
               id = id[:-1]
               break
               
            if found:
                id+=i
        id = id.split(" ")
        if len(id)>=2:
            for item in id:
                self.id[item.split("=")[0]] = item.split("=")[1][1:-1]
        else:
            self.id["id"] = ""
            
        self.parseXMLString(self.src)
        



    def __str__(self):
        return self.src
        
        
    def lzaData(self):
        if self.id["id"]=="mediatum_metadata":
            return True
        return False
     
    # if there is still an original comment inside add add old as object
    def addOriginal(self, src):
        self.original = src
        lines = self.src.split("\r\n")
        lines.insert(1, "    <metadata>")
        lines.insert(2, "        <old>")
        lines.insert(3, "            <COM>" + self.original + "</COM>")
        lines.insert(4, "        </old>")
        lines.insert(-1, "    </metadata>")
        self.src = "\r\n".join(lines)
        self.parseXMLString(self.src)
        
    # get content of old comment    
    def GetOriginal(self):
        if len(self.obj.children)>0 and self.obj.children[0].name=="old":
            return self.obj.children[0].children[0].value
        else:
            return ""

        
    def parseXMLString(self, src):
        self._attr = []
        self._path = []
        self.obj = None
        self.actObj = None
        
        def getParent(obj, path):
            if obj.path==path[:-1]:
                return obj
            else:
                for child in obj.children:
                    p = getParent(child, path)
                    if p:
                        return p

        
        def start_element(name, attrs):
            
            self._path.append(u(name))
            
            self.actObj = MetadataItem(self._path[-1], self._path, "", attrs)
            if self.obj==None:
                self.obj = self.actObj
            else:
                found = False
                item = getParent(self.obj, self.actObj.path)
                
                if item:
                    item.addChild(self.actObj)
                else:
                    raise "syntax error"


        def end_element(name):
            self._path.pop()
  
        def char_data(data):
            if data.strip()!="":
                self.actObj.value = data

        p = xml.parsers.expat.ParserCreate()

        p.StartElementHandler = start_element
        p.EndElementHandler = end_element
        p.CharacterDataHandler = char_data
        p.Parse(src)
  
        
    def getXMLMetaString(self, obj=None, indent=0, ret=""):
        if not obj:
            obj = self.obj
        ret += '\r\n' + ('    ' * indent) + '<' + u(obj.path[-1])
        if len(obj.attr)>0:
            for item in obj.attr:
                ret += ' ' + u(item) + '="' + u(obj.attr[item]) + '"'
        
        ret += '>'
        if len(obj.children)>0:
            for item in obj.children:
                ret += self.getXMLMetaString(item, indent + 1)
            ret += '\r\n' + ('    ' * indent) + '</' + u(obj.path[-1]) + '>'
        else:
            ret += u(obj.value)
            ret += '</' + u(obj.path[-1]) + '>'
        return ret
 

# supported filetypes
from jpeg import JPEGImage
from pdf import PDFDocument  
from tiff import TIFFImage    
        
class LZA:

    def __init__(self, filename):
        self.item = None
        if filename.endswith(".pdf"):
            self.item = PDFDocument(filename)
        elif filename.endswith(".tiff"):
            self.item = TIFFImage(filename)
        elif filename.endswith(".jpg") or filename.endswith(".jpeg"):
            self.item = JPEGImage(filename)
        else:
            raise "filetype not supported"


    def writeMediatumData(self, data, outputfile=""):    
        self.item.writeMetaData(str(data), outputfile)


    def getMediatumData(self):
        meta = self.item.getMetaData()
        if meta.lzaData():
            return meta
        else:
            return ""


    def getOriginal(self, outputfile=""):
        self.item.getOriginal(outputfile)
        
        
