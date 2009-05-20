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
import core.tree as tree
import socket
import random
import core.config as config
import utils.date
from utils.dicts import MaxSizeDict
import utils.date as date
import core.acl as acl
import core.xmlnode
from utils.utils import esc,getCollection

errordesc = {
 "badArgument": "The request includes illegal arguments, is missing required arguments, includes a repeated argument, or values for arguments have an illegal syntax.",
 "badResumptionToken": "The value of the resumptionToken argument is invalid or expired.",
 "badVerb": "none or no valid OAI verb",
 "cannotDisseminateFormat": "The metadata format identified by the value given for the metadataPrefix argument is not supported by the item or by the repository.",
 "idDoesNotExist": "The value of the identifier argument is unknown or illegal in this repository.",
 "noRecordsMatch": "The combination of the values of the from, until, set and metadataPrefix arguments results in an empty list.",
 "noMetadataFormats": "There are no metadata formats available for the specified item.",
 "noSetHierarchy": "The repository does not support sets.",
 "noPermission": "The requested records are protected",
 "badDateformatUntil" : "Bad argument (until): Date not in OAI format (yyyy-mm-dd or yyyy-mm-ddThh:mm:ssZ)",
 "badDateformatFrom" : "Bad argument (from): Date not in OAI format (yyyy-mm-dd or yyyy-mm-ddThh:mm:ssZ)",
}

EARLIEST_YEAR=1960
CHUNKSIZE=10

#-----
#class Export:
#    def __init__(self, metaDataPrefix, schema, nameSpace):
#        self.metaDataPrefix = metaDataPrefix
#        self.schema = schema
#        self.nameSpace = nameSpace
#
#exports = {
#    "epicur": Export("epicur", "urn:nbn:de:1111-2004033116 http://nbn-resolving.de/urn/resolver.pl?urn=urn:nbn:de:1111-2004033116", "urn:nbn:de:1111-2004033116"),
#    "xmetadiss": Export("xmetadiss", "http://www.ddb.de/standards/xmetadiss/xmetadiss.xsd", "http://www.ddb.de/standards/xMetaDiss/")
#}
#-----

def mklink(req):
    return "http://"+config.get("host.name", socket.gethostname()+":8081")+"/oai/oai"

def writeHead(req, attributes=""):
    request = mklink(req)
    d = ISO8601(date.now())
    try:
        verb = req.params["verb"]
    except KeyError:
        verb = ""

    req.write("""<?xml version="1.0" encoding="UTF-8"?>
    <OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.openarchives.org/OAI/2.0/ http://www.openarchives.org/OAI/2.0/OAI-PMH.xsd">
        <responseDate>"""+d+"""Z</responseDate>
        <request""")
    if attributes!="noatt":
        for n in "verb", "identifier", "metadataprefix", "from", "until", "set":
            if n in req.params:
                req.write(' '+n+'="'+esc(req.params[n])+'"')
    req.write(">"+request+"</request>")

def writeTail(req):
    req.write("""</OAI-PMH>""")

def writeError(req, code, detail=""):
    d = ISO8601(date.now())
    try:
        verb = req.params["verb"]
    except KeyError:
        verb = ""
    if detail!="":
        req.write("""<error code="%s">%s</error>""" % (code, errordesc[detail]))
    else:
        req.write("""<error code="%s">%s</error>""" % (code, errordesc[code]))

def ISO8601(t=None):
    # MET summer time 
    if t is None:
        t = date.now()
    return "%0.4d-%0.2d-%0.2dT%0.2d:%0.2d:%0.2d" % (t.year, t.month, t.day, t.hour, t.minute, t.second)

def parseDate(string):
    if string.endswith("Z"):
        string = string[:-1]
    try:
        return date.parse_date(string, "%Y-%m-%d")
    except:
        try:
            return date.parse_date(string, "%Y-%m-%dT%H:%M:%S")
        except:
            return date.parse_date(string[12:], "%Y-%m-%d")

def checkParams(req, list):
    params = req.params.copy()
    for entry in list:
        if entry not in params:
            return 0
        del params[entry]
    if len(params)>0:
        return 0
    return 1

# FIXME: metadataformats are currently hardcoded- should depend on collection

def ListMetadataFormats(req):
    if "identifier" in req.params:
        id = identifier2id(req.params["identifier"])
        try:
            node = tree.getNode(id)
        except TypeError:
            return writeError(req,"badArgument")
        except KeyError:
            return writeError(req,"badArgument")
        except tree.NoSuchNodeError:
            return writeError(req,"badArgument")
    req.write("""
       <ListMetadataFormats>

         <metadataFormat>
             <metadataPrefix>oai_dc</metadataPrefix>
             <schema>http://www.openarchives.org/OAI/2.0/oai_dc.xsd</schema>
             <metadataNamespace>http://www.openarchives.org/OAI/2.0/oai_dc/</metadataNamespace>
         </metadataFormat>

         <metadataFormat>
             <metadataPrefix>epicur</metadataPrefix>
             <schema>urn:nbn:de:1111-2004033116 http://nbn-resolving.de/urn/resolver.pl?urn=urn:nbn:de:1111-2004033116</schema>
             <metadataNamespace>urn:nbn:de:1111-2004033116</metadataNamespace>
         </metadataFormat>

         <metadataFormat>
             <metadataPrefix>xmetadiss</metadataPrefix>
             <schema>http://www.ddb.de/standards/xmetadiss/xmetadiss.xsd</schema>
             <metadataNamespace>http://www.ddb.de/standards/xMetaDiss/</metadataNamespace>
         </metadataFormat>
         
         <metadataFormat>
             <metadataPrefix>mediatum</metadataPrefix>
             <schema>http://mediatum-pages.ub.tum.de/mediatum.xsd</schema>
             <metadataNamespace>http://mediatum-pages.ub.tum.de/</metadataNamespace>
         </metadataFormat>
       </ListMetadataFormats>
    """)

def checkMetaDataFormat(format):
    return format in ["epicur", "xmetadiss", "oai_dc", "mediatum"]

def Identify(req):
    if not checkParams(req, ["verb"]):
        print "Identify: verb missing"
        return writeError(req, "badArgument")
    request = mklink(req)
    root = tree.getRoot()
    if config.get("config.oaibasename")=="":
        name = root.getName()
    else:
        name = config.get("config.oaibasename")
    req.write("""
        <Identify>
            <repositoryName>"""+name+"""</repositoryName>
            <baseURL>"""+request+"""</baseURL>
            <protocolVersion>2.0</protocolVersion>
            <adminEmail>"""+config.get("email.admin")+"""</adminEmail>
            <earliestDatestamp>"""+str(EARLIEST_YEAR-1)+"""-01-01T12:00:00Z</earliestDatestamp>
            <deletedRecord>no</deletedRecord>
            <granularity>YYYY-MM-DDThh:mm:ssZ</granularity>
       </Identify>""")

#DATEFIELD="date-accepted"
DATEFIELD="updatetime"

def writeRecord(req, node, metadataformat):
    collection = getCollection(node)
    updatetime = node.get(DATEFIELD)
    if updatetime:
        d = ISO8601(date.parse_date(updatetime))
    else:
        d = ISO8601(date.DateTime(EARLIEST_YEAR-1,12,31,23,59,59))

    req.write(""" 
           <record>
               <header><identifier>"""+mkIdentifier(node.id)+"""</identifier>
                       <datestamp>"""+d+"""Z</datestamp>
                       <setSpec>"""+collection.id+"""</setSpec>
               </header>
               <metadata>""")

    #<dc: xmlns:dc="http://purl.org/dc/elements/1.1/" 
    #     xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
    #     xsi:schemaLocation="http://purl.org/dc/elements/1.1/">""")
    #for f in "title", "creator", "contributor", "type", "source", "language", "identifier": 
    #    value = node.get(f)
    #    req.write("""<dc:%s>%s</dc:%s>""" % (f,value,f))

    if metadataformat=="mediatum":
        req.write(core.xmlnode.getSingleNodeXML(node))
    else:
        if hasattr(node, "getXML"):
            req.write(node.getXML(metadataformat))
        else:
            req.write("<recordHasNoXMLRepresentation/>")

    req.write("""</metadata></record>""")

IDPREFIX = "oai:mediatum2.ub.tum.org:node/"

def mkIdentifier(id):
    return IDPREFIX+id

def identifier2id(id):
    if id.startswith(IDPREFIX):
        return id[len(IDPREFIX):]
    else:
        return id

def retrieveNodes(access, collectionid, date_from=None, date_to=None, metadataformat=None):
    if collectionid:
        collection = tree.getNode(collectionid)
    else:
        collection = tree.getRoot("collections")
   
    if metadataformat == "mediatum":
        query = "objtype=document"
    else:
        query = "objtype=dissertation and schema=diss"

    if date_from:
        if query:
            query += " and "
        query += DATEFIELD + " >= "+str(date_from)
    if date_to:
        if query:
            query += " and "
        query += DATEFIELD + " <= "+str(date_to)
    nodes = collection.search(query)
    print "nodes", nodes
    if access:
        nodes = access.filter(nodes)

    print "search below",collection.id,collection.name,"for",query,":",len(nodes),"nodes"
    
    return nodes


tokenpositions = MaxSizeDict(32)

def getNodes(req):
    global tokenpositions,CHUNKSIZE
    access = acl.AccessData(req)
    nodes = None
    try:
        token = req.params["resumptionToken"]
        try:
            pos,nodes,metadataformat = tokenpositions[token]
        except KeyError:
            return None,"badResumptionToken",None
        if not checkParams(req, ["verb", "resumptionToken"]):
            print "getNodes: additional arguments (only verb and resumptionToken allowed)"
            return None,"badArgument",None
    except KeyError:
        token = str(random.random())
        tokenpositions[token] = pos = 0

        metadataformat = req.params.get("metadataPrefix",None)
        if not checkMetaDataFormat(metadataformat):
            print "ListRecords: metadataPrefix missing"
            return None,"badArgument",None
      
    if nodes is None:
        string_from,string_to = None,None
        try:
            string_from = req.params["from"]
            date_from = parseDate(string_from)
            if date_from.year<EARLIEST_YEAR:
                date_from=date.DateTime(0,0,0,0,0,0)
        except:
            if "from" in req.params:
                return None,"badArgument",None
            date_from = None
        try:
            date_to = parseDate(req.params["until"])
            if not date_to.has_time:
                date_to.hour = 23
                date_to.minute = 59
                date_to.second = 59
            if date_to.year<EARLIEST_YEAR-1:
                raise
            string_to = req.params["until"]
        except:
            if "until" in req.params:
                return None,"badArgument",None
            date_to = None
        try:
            collectionid = req.params["set"]
        except:
            collectionid = None

        if string_from and string_to and (string_from > string_to or len(string_from) != len(string_to)):
            return None,"badArgument",None

        try:
            nodes = retrieveNodes(access, collectionid, date_from, date_to, metadataformat)
        except tree.NoSuchNodeError:
            # collection doesn't exist
            return None,"badArgument",None
    
    tokenpositions[token] = pos + CHUNKSIZE, nodes, metadataformat

    tokenstring = '<resumptionToken expirationDate="'+ISO8601(date.now().add(3600*24))+'" '+ \
                   'completeListSize="'+str(len(nodes))+'" cursor="'+str(pos)+'">'+token+'</resumptionToken>'
    if pos + CHUNKSIZE > len(nodes):
        tokenstring = None
        del tokenpositions[token]
    return tree.NodeList(nodes[pos:pos+CHUNKSIZE]), tokenstring, metadataformat

def ListIdentifiers(req):
    #if "until" in req.params.keys():
    #    return writeError(req, 'badArgument')
    nodes, tokenstring, metadataformat = getNodes(req)
    if nodes is None:
        return writeError(req,tokenstring)
    if not len(nodes):
        return writeError(req,'noRecordsMatch')

    req.write("""<ListIdentifiers>""")
    for n in nodes:
        updatetime = n.get(DATEFIELD)
        if updatetime:
            d = ISO8601(date.parse_date(updatetime))
        else:
            d = ISO8601()
        req.write("""<header><identifier>"""+mkIdentifier(n.id)+"""</identifier><datestamp>"""+d+"""Z</datestamp></header>\n""")
    if tokenstring:
        req.write(tokenstring)
    req.write("""</ListIdentifiers>""")

def ListRecords(req):

    eyear = str(EARLIEST_YEAR-1)+"""-01-01T12:00:00Z"""
    if "until" in req.params.keys() and req.params.get("until")<eyear and len(req.params.get("until"))==len(eyear):
        return writeError(req, 'noRecordsMatch')
    if "resumptionToken" in req.params.keys() and "until" in req.params.keys():
        return writeError(req, 'badArgument')
        
    nodes, tokenstring, metadataformat = getNodes(req)
    if nodes is None:
        return writeError(req,tokenstring)
    if not len(nodes):
        return writeError(req,'noRecordsMatch')

    req.write("""<ListRecords>""")
    for n in nodes:
        writeRecord(req, n, metadataformat)
    if tokenstring:
        req.write(tokenstring)
    req.write("""</ListRecords>""")

def GetRecord(req):
    access = acl.AccessData(req)
    try:
        id = req.params["identifier"]
    except KeyError:
        print "GetRecords: identifier missing"
        return writeError(req,"badArgument")
        
    metadataformat = req.params.get("metadataPrefix",None)
    if not checkMetaDataFormat(metadataformat):
        print "GetRecord: metadataPrefix missing"
        return writeError(req,"badArgument")

    id = identifier2id(id)
    
    print id

    try:
        node = tree.getNode(id)
    except TypeError:
        return writeError(req,"idDoesNotExist")
    except KeyError:
        return writeError(req,"idDoesNotExist")
    except tree.NoSuchNodeError:
        return writeError(req,"idDoesNotExist")

    if not access.hasReadAccess(node):
        return writeError(req,"noPermission")

    req.write("""<GetRecord>""")
    writeRecord(req, node, metadataformat)
    req.write("""</GetRecord>""")

def ListSets(req):
    access = acl.AccessData(req)
    req.write("""<ListSets>""")
    def browse(collection):
        for c in access.filter(collection.getChildren()):
            if c.type=="collection":
                spec = c.id
                name = c.getName()
                req.write("""<set><setSpec>"""+spec+"""</setSpec><setName>"""+esc(name)+"""</setName></set>""")
                browse(c)
    browse(tree.getRoot("collections"))
    req.write("""</ListSets>""")

def oaiRequest(req):
    req.request["Content-Type"] = "text/xml"

    if "until" in req.params:
        try:
            date_to = parseDate(req.params["until"])
        except:
            writeHead(req, "noatt")  
            writeError(req, "badArgument", "badDateformatUntil")
            writeTail(req)
            return
            
    elif "from" in req.params:
        try:
            date_from = parseDate(req.params["from"])
        except:
            writeHead(req, "noatt")
            writeError(req, "badArgument", "badDateformatFrom")
            writeTail(req)
            return

    if "verb" not in req.params:
        writeError(req,"badVerb")
    
    else:
        verb = req.params["verb"]
        if verb == "Identify":
            writeHead(req)
            Identify(req)
        elif verb == "ListMetadataFormats":
            writeHead(req)
            ListMetadataFormats(req)
        elif verb == "ListSets":
            writeHead(req)
            ListSets(req)
        elif verb == "ListIdentifiers":
            writeHead(req)
            ListIdentifiers(req)
        elif verb == "ListRecords":
            writeHead(req)
            ListRecords(req)
        elif verb == "GetRecord":
            writeHead(req)
            GetRecord(req)
        else:
            writeHead(req, "noatt")
            writeError(req,"badVerb")

    writeTail(req)



