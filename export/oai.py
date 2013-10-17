"""
 mediatum - a multimedia content repository

 Copyright (C) 2007 Arne Seifert <seiferta@in.tum.de>
 Copyright (C) 2007 Matthias Kramm <kramm@in.tum.de>
 Copyright (C) 2011 Werner Neudenberger <neudenberger@ub.tum.de>
 

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
import re
import time
import sys
import logging
import core.config as config
import core.users as users

from oaisearchparser import OAISearchParser as OAISearchParser
from utils.dicts import MaxSizeDict
import oaisets
import utils.date as date
import core.acl as acl
import core.xmlnode
from utils.utils import esc, fixXMLString
from schema.schema import getMetaType
from utils.pathutils import isDescendantOf
from exportutils import is_active_version

if sys.version[0:3] < '2.6':
    import simplejson as json
else:
    import json

DEBUG = False

DATEFIELD = config.get("oai.datefield", "updatetime")
EARLIEST_YEAR = int(config.get("oai.earliest_year", "1960"))
CHUNKSIZE = int(config.get("oai.chunksize", "10"))
IDPREFIX = config.get("oai.idprefix", "oai:mediatum.org:node/")
SAMPLE_IDENTIFIER = config.get("oai.sample_identifier", "oai:mediatum.org:node/123")
tokenpositions = MaxSizeDict(32)

SET_LIST = [] 
FORMAT_FILTERS = {}

def registerFormatFilter(key, filterFunc):
    global FORMAT_FILTERS
    FORMAT_FILTERS[key.lower()] = filterFunc
    
def filterFormat(node, oai_format):
    if oai_format.lower() in FORMAT_FILTERS.keys():
        return FORMAT_FILTERS[oai_format.lower()](node)
    return True

def OUT(msg, type="info"):
    if DEBUG:
        sys.stdout.flush()
    if type=="info":
        logging.getLogger('oai').info(msg)
    elif type=="error":
        logging.getLogger('oai').error(msg)
        
def now():
    return time.clock()
    
def make_lookup_key(req):
    return "%s:%d" % (req.ip, req.channel.addr[1])

def timetable_update(req, msg):
    if req:
        req._tt['tlist'].append((msg, now()))
        
def timetable_string(req):
    s = ''+('-'*80)
    s += "\n| timetable for request %s" % (req.uri)
    atime = req._tt['atime']
    count = 0
    for i, (msg, t) in enumerate(req._tt['tlist']):
        duration = t - atime
        atime = t
        count += 1
        s += "\n|  %2d. step: %.3f sec.: %s" % (i, duration, msg) 
    return s + '\n'+('-'*80) 

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


def mklink(req):
    return "http://"+config.get("host.name", socket.gethostname()+":8081")+"/oai/oai"

def writeHead(req, attributes=""):
    request = mklink(req)
    d = ISO8601(date.now())
    try:
        verb = req.params["verb"]
    except KeyError:
        verb = ""
    req.reply_headers['charset'] = 'utf-8'
    req.reply_headers['Content-Type'] = 'text/xml; charset=utf-8'
    req.write("""<?xml version="1.0" encoding="UTF-8"?>
    <OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.openarchives.org/OAI/2.0/ http://www.openarchives.org/OAI/2.0/OAI-PMH.xsd">
        <responseDate>%sZ</responseDate>
        <request""" %(ISO8601(date.now())))
    if attributes!="noatt":
        for n in ["verb", "identifier", "metadataprefix", "from", "until", "set"]:
            if n in req.params:
                req.write(' %s="%s"' %(n, esc(req.params[n])))
    req.write('>%s</request>' %(request))
    if DEBUG:
        timetable_update(req, "leaving writeHead")

def writeTail(req):
    req.write('</OAI-PMH>')
    if DEBUG:
        timetable_update(req, "leaving writeTail")    

def writeError(req, code, detail=""):
    if not "verb" in req.params:
        verb = ""

    if detail!="":
        desc = errordesc[detail] 
    else:
        desc = errordesc[code] 
    req.write('<error code="%s">%s</error>' %(code, desc))
    msg = "%s:%d OAI (error code: %s) %s" % (req.ip, req.channel.addr[1], (code), (req.path + req.uri).replace('//','/'))
    OUT(msg, 'error')    

        
def ISO8601(t=None):
    # MET summer time
    if not t:
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
    
def getExportMasks(regexp):
    exportmasks = [tree.getNode(nid) for nid in tree.getNodesByAttribute('masktype', 'export')]
    exportmasks = [(n, n.name) for n in exportmasks if re.match(regexp, n.name) and n.type=='mask']
    dict_metadatatype2exportmask = {}
    for exportmask in exportmasks:
        parents = exportmask[0].getParents()
        try:
            mdt_node = [p for p in parents if p.type == 'metadatatype'][0]
            mdt = (mdt_node, mdt_node.name)
            dict_metadatatype2exportmask[mdt] = dict_metadatatype2exportmask.setdefault(mdt, []) + [exportmask]
        except:
            pass
    return dict_metadatatype2exportmask.items()

def getOAIExportFormatsForSchema(schema_name):
    try:
        schema_node = [x for x in tree.getRoot('metadatatypes').getChildren() if x.name==schema_name][0]
        res = [x.name for x in schema_node.getChildren() if (x.type=='mask' and x.get('masktype')=='export')]
        return [x.replace('oai_','',1) for x in res if x.startswith('oai_')]
    except:
        OUT("ERROR in getOAIExportMasksForSchema('%s'):\n%s %s" % (schema_name, str(sys.exc_info()[0]), str(sys.exc_info()[1])), 'error')
        return []

def getOAIExportFormatsForIdentifier(identifier):
    try:
        node = tree.getNode(identifier2id(identifier))
    except:
        return []
    return getOAIExportFormatsForSchema(node.getSchema())

def nodeHasOAIExportMask(node, metadataformat):
    if node.getSchema() in [x[0][1] for x in getExportMasks('oai_%s$' % metadataformat)]:
        return True
    return False

def ListMetadataFormats(req):
    if "set" in req.params:
        return writeError(req, "badArgument")

    # supported oai metadata formats are configured in section
    # oai.formats in the mediatum.cfg file
    d = config.getsubset('oai')
    formats = [x.strip() for x in d['formats'].split(',') if x.strip()]

    if "identifier" in req.params:
        # list only formats available for the given identifier
        try:
            node = tree.getNode(identifier2id(req.params.get("identifier")))
        except (TypeError, KeyError, tree.NoSuchNodeError):
            return writeError(req,"badArgument")

        access = acl.AccessData(req)    
        if not access.hasReadAccess(node):
            return writeError(req, "noPermission")    
            
        formats = [x for x in formats if nodeHasOAIExportMask(node, x.lower())]
        formats = [x for x in formats if filterFormat(node, x.lower())]

    # write xml for metadata formats list
    req.write('\n      <ListMetadataFormats>\n')
    for mdf in formats:
        try:
            req.write("""
             <metadataFormat>
               <metadataPrefix>%s</metadataPrefix>
               <schema>%s</schema>
               <metadataNamespace>%s</metadataNamespace>
             </metadataFormat>
             """ % (mdf, d["schema.%s" % mdf], d["namespace.%s" % mdf]) )
        except:
            OUT("%s: OAI error reading oai metadata format %s from config file" % (__file__, mdf), 'error')
    req.write('\n</ListMetadataFormats>')
    if DEBUG:
        timetable_update(req, "leaving ListMetadataFormats")    

def checkMetaDataFormat(format):
    d = config.getsubset('oai')
    try:
        return format.lower() in [x.strip().lower() for x in d['formats'].split(',') if x.strip()]
    except:
        return False

def Identify(req):
    if not checkParams(req, ["verb"]):
        return writeError(req, "badArgument")
    if config.get("config.oaibasename")=="":
        root = tree.getRoot()
        name = root.getName()
    else:
        name = config.get("config.oaibasename")
    req.write("""
        <Identify>
          <repositoryName>%s</repositoryName>
          <baseURL>%s</baseURL>
          <protocolVersion>2.0</protocolVersion>
          <adminEmail>%s</adminEmail>
          <earliestDatestamp>%s-01-01T12:00:00Z</earliestDatestamp>
          <deletedRecord>no</deletedRecord>
          <granularity>YYYY-MM-DDThh:mm:ssZ</granularity>
          <description>
            <oai-identifier xmlns="http://www.openarchives.org/OAI/2.0/oai-identifier" xsi:schemaLocation="http://www.openarchives.org/OAI/2.0/oai-identifier http://www.openarchives.org/OAI/2.0/oai-identifier.xsd">
              <scheme>oai</scheme>
              <repositoryIdentifier>%s</repositoryIdentifier>
              <delimiter>:</delimiter>
              <sampleIdentifier>%s</sampleIdentifier>
            </oai-identifier>
          </description>
        </Identify>""" %(name, mklink(req), config.get("email.admin"), str(EARLIEST_YEAR-1), config.get("host.name", socket.gethostname()), SAMPLE_IDENTIFIER))
    if DEBUG:
        timetable_update(req, "leaving Identify")   

def getSetSpecsForNode(node):
    setspecs = oaisets.getSetSpecsForNode(node)
    setspecs_elements = ["<setSpec>%s</setSpec>" % setspec for setspec in setspecs]
    indent = '\n    '
    return indent + (indent.join(setspecs_elements))

def writeRecord(req, node, metadataformat):
    global SET_LIST
    if not SET_LIST:
        initSetList(req)

    updatetime = node.get(DATEFIELD)
    if updatetime:
        d = ISO8601(date.parse_date(updatetime))
    else:
        d = ISO8601(date.DateTime(EARLIEST_YEAR-1,12,31,23,59,59))

    set_specs = getSetSpecsForNode(node)
    
    if DEBUG: timetable_update(req, " in writeRecord: getSetSpecsForNode: node: '%s, %s', metadataformat='%s' set_specs:%s" % ( str(node.id), node.type, metadataformat, str(set_specs)))   
    
    req.write("""
           <record>
               <header><identifier>%s</identifier>
                       <datestamp>%sZ</datestamp>
                       %s
               </header>
               <metadata>""" %(mkIdentifier(node.id), d, set_specs))
               
    if DEBUG: timetable_update(req, " in writeRecord: writing header: node.id='%s', metadataformat='%s'" % ( str(node.id), metadataformat ) )            

    if metadataformat=="mediatum":
        req.write(core.xmlnode.getSingleNodeXML(node))
    elif nodeHasOAIExportMask(node, metadataformat.lower()): # in [masknode.name for masknode in getMetaType(node.getSchema()).getMasks() if masknode.get('masktype')=='exportmask']:
        mask = getMetaType(node.getSchema()).getMask("oai_"+metadataformat.lower())
        if DEBUG: timetable_update(req, """ in writeRecord: mask = getMetaType(node.getSchema()).getMask("oai_"+metadataformat.lower()): node.id='%s', metadataformat='%s'""" % ( str(node.id), metadataformat ) ) 
        try:
            req.write(fixXMLString(mask.getViewHTML([node], flags=8))) # fix xml errors
        except:
            req.write(mask.getViewHTML([node], flags=8))
        if DEBUG: timetable_update(req, " in writeRecord: req.write(mask.getViewHTML([node], flags=8)): node.id='%s', metadataformat='%s'" % ( str(node.id), metadataformat ) ) 
        
    else:
        req.write('<recordHasNoXMLRepresentation/>')

    req.write('</metadata></record>')
    
    if DEBUG: timetable_update(req, "leaving writeRecord: node.id='%s', metadataformat='%s'" % ( str(node.id), metadataformat ) )     


def mkIdentifier(id):
    return IDPREFIX+id

def identifier2id(id):
    if id.startswith(IDPREFIX):
        return id[len(IDPREFIX):]
    return id

# exclude children of media
def parentIsMedia(n):
    try:
        p = n.getParents()[0]
        return hasattr(p, "isContainer") and p.isContainer()==0
    except IndexError:
        print '---> IndexError in export.oai.parentIsMedia(...)', n, n.id, n.type, n.name
        return True

def concatNodeLists(nodelist1, nodelist2):
    try:
        return tree.NodeList(list(set(nodelist1.getIDs() + nodelist2.getIDs())))
    except:
        return tree.NodeList(list(set(nodelist1.getIDs() + list(nodelist2))))    

def retrieveNodes(req, access, setspec, date_from=None, date_to=None, metadataformat=None):
    schemata = []
    
    if metadataformat == 'mediatum':
        metadatatypes = tree.getRoot('metadatatypes').getChildren()
        schemata = [m.name for m in metadatatypes if m.type=='metadatatype' and not m.name in ['directory', 'collection']]
    elif metadataformat:
        mdt_masks_list = getExportMasks("oai_"+metadataformat.lower()+"$") # check exact name
        schemata = [x[0][1] for x in mdt_masks_list if x[1]]
        
    if DEBUG: timetable_update(req, "in retrieveNodes: find schemata with export mask for metadata type %s (%d found: '%s')" % (metadataformat.lower(), len(schemata), str([x for x in schemata])))        

    if setspec:
        res = oaisets.getNodes(setspec, schemata)
    else:
        osp = OAISearchParser()
        query = " or ".join(["schema=%s" % schema for schema in schemata])
        res = osp.parse(query).execute()    
    
    res = tree.NodeList(res)
    if DEBUG: timetable_update(req, "in retrieveNodes: after building NodeList for %d nodes" % (len(res)))

    if date_from:
        res = [n for n in res if n.get(DATEFIELD)>=str(date_from)]
        if DEBUG: timetable_update(req, "in retrieveNodes: after filtering date_from --> %d nodes" % (len(res)))
    if date_to:
        res = [n for n in res if n.get(DATEFIELD)<=str(date_to)] 
        if DEBUG: timetable_update(req, "in retrieveNodes: after filtering date_to --> %d nodes" % (len(res))) 
        
    if access:
        res = access.filter(res)
        if DEBUG: timetable_update(req, "in retrieveNodes: after access filter --> %d nodes" % (len(res)))         
        
    collections = tree.getRoot('collections')    
    res = [n for n in res if isDescendantOf(n, collections)]
    if DEBUG: timetable_update(req, "in retrieveNodes: after checking descendance from basenode --> %d nodes" % (len(res)))          
    
    if schemata:
        res = [n for n in res if n.getSchema() in schemata]
        if DEBUG: timetable_update(req, "in retrieveNodes: after schemata (%s) filter --> %d nodes" % (str(schemata), len(res)))    
        
    if metadataformat and metadataformat.lower() in FORMAT_FILTERS.keys():
        format_string = metadataformat.lower()
        res = [n for n in res if filterFormat(n, format_string)]
        if DEBUG: timetable_update(req, "in retrieveNodes: after format (%s) filter --> %d nodes" % (format_string, len(res)))          
        
    return res       

def getNodes(req):
    global tokenpositions,CHUNKSIZE
    access = acl.AccessData(req)
    nodes = None

    if "resumptionToken" in req.params:
        token = req.params.get("resumptionToken")
        if token in tokenpositions:
            pos, nodes, metadataformat = tokenpositions[token]
        else:
            return None, "badResumptionToken", None

        if not checkParams(req, ["verb", "resumptionToken"]):
            OUT("OAI: getNodes: additional arguments (only verb and resumptionToken allowed)")
            return None, "badArgument", None

    else:
        token = str(random.random())
        tokenpositions[token] = pos = 0

        metadataformat = req.params.get("metadataPrefix", None)
        if not checkMetaDataFormat(metadataformat):
            OUT('OAI: ListRecords: metadataPrefix missing', 'error')
            return None, "badArgument", None

    if not nodes:
        string_from, string_to = None, None
        try:
            string_from = req.params["from"]
            date_from = parseDate(string_from)
            if date_from.year<EARLIEST_YEAR:
                date_from = date.DateTime(0,0,0,0,0,0)
        except:
            if "from" in req.params:
                return None, "badArgument", None
            date_from = None
            
        try:
            date_to = parseDate(req.params["until"])
            string_to = req.params.get("until")
            if not date_to.has_time:
                date_to.hour = 23
                date_to.minute = 59
                date_to.second = 59
            if date_to.year<EARLIEST_YEAR-1:
                raise
        except:
            if "until" in req.params:
                return None,"badArgument",None
            date_to = None

        setspec = None
        if "set" in req.params:
            setspec = req.params.get("set")
        
        if string_from and string_to and (string_from > string_to or len(string_from) != len(string_to)):
            return None, "badArgument", None

        try:
            nodes = retrieveNodes(req, access, setspec, date_from, date_to, metadataformat)
            nodes = [n for n in nodes if not parentIsMedia(n)]
            # filter out nodes that are inactive or older versions of other nodes
            nodes = [n for n in nodes if is_active_version(n)] 
        except tree.NoSuchNodeError:
            # collection doesn't exist
            return None, "badArgument", None

    tokenpositions[token] = pos + CHUNKSIZE, nodes, metadataformat
    tokenstring = '<resumptionToken expirationDate="'+ISO8601(date.now().add(3600*24))+'" '+ \
                   'completeListSize="'+str(len(nodes))+'" cursor="'+str(pos)+'">'+token+'</resumptionToken>'
    if pos + CHUNKSIZE>=len(nodes):
        tokenstring = None
        del tokenpositions[token]
    OUT(req.params.get('verb')+": set="+str(req.params.get('set'))+", "+ str(len(nodes))+" objects, format="+metadataformat)
    res = tree.NodeList(nodes[pos:pos+CHUNKSIZE])
    if DEBUG: timetable_update(req, "leaving getNodes: returning %d nodes, tokenstring='%s', metadataformat='%s'" % (len(res), tokenstring, metadataformat) )
         
    return res, tokenstring, metadataformat

def ListIdentifiers(req):

    global SET_LIST
    if not SET_LIST:
        initSetList(req)

    nodes, tokenstring, metadataformat = getNodes(req)
    if nodes is None:
        return writeError(req,tokenstring)
    if not len(nodes):
        return writeError(req,'noRecordsMatch')

    req.write('<ListIdentifiers>')
    for n in nodes:
        updatetime = n.get(DATEFIELD)
        if updatetime:
            d = ISO8601(date.parse_date(updatetime))
        else:
            d = ISO8601()
        req.write('<header><identifier>%s</identifier><datestamp>%sZ</datestamp>%s\n</header>\n' %(mkIdentifier(n.id), d, getSetSpecsForNode(n)))
    if tokenstring:
        req.write(tokenstring)
    req.write('</ListIdentifiers>')
    if DEBUG: timetable_update(req, "leaving ListIdentifiers")     


def ListRecords(req):
    eyear = str(EARLIEST_YEAR-1)+"""-01-01T12:00:00Z"""
    if "until" in req.params.keys() and req.params.get("until")<eyear and len(req.params.get("until"))==len(eyear):
        return writeError(req, 'noRecordsMatch')
    if "resumptionToken" in req.params.keys() and "until" in req.params.keys():
        return writeError(req, 'badArgument')

    nodes, tokenstring, metadataformat = getNodes(req)
    # getNodes(req) filtered out nodes that are inactive or older versions of other nodes
    if nodes is None:
        return writeError(req,tokenstring)
    if not len(nodes):
        return writeError(req,'noRecordsMatch')

    req.write('<ListRecords>')
    for n in nodes:
        writeRecord(req, n, metadataformat)
    if tokenstring:
        req.write(tokenstring)
    req.write('</ListRecords>')
    if DEBUG:
        timetable_update(req, "leaving ListRecords")     


def GetRecord(req):
    access = acl.AccessData(req)
    if "identifier" in req.params:
        id = identifier2id(req.params.get("identifier"))
    else:
        return writeError(req,"badArgument")

    metadataformat = req.params.get("metadataPrefix",None)
    if not checkMetaDataFormat(metadataformat):
        return writeError(req,"badArgument")

    try:
        node = tree.getNode(id)
    except (TypeError, KeyError, tree.NoSuchNodeError):
        return writeError(req, "idDoesNotExist")
        
    if metadataformat and (metadataformat.lower() in FORMAT_FILTERS.keys()) and not filterFormat(node, metadataformat.lower()):
        return writeError(req, "noPermission")
        
    if parentIsMedia(node):
        return writeError(req, "noPermission")

    if not access.hasReadAccess(node):
        return writeError(req,"noPermission")

    req.write('<GetRecord>')
    writeRecord(req, node, metadataformat)
    req.write('</GetRecord>')
    if DEBUG: timetable_update(req, "leaving GetRecord")     
    
def ListSets(req):
    # new container sets may have been added
    initSetList(req)
    req.write('\n<ListSets>')
    
    for setspec, setname in oaisets.getSets():
        req.write('\n <set><setSpec>%s</setSpec><setName>%s</setName></set>' %(setspec, setname))
        
    req.write('\n</ListSets>')
    if DEBUG: timetable_update(req, "leaving ListSets")     
    
def initSetList(req=None):
    global SET_LIST
    if req:    
        access = acl.AccessData(req)
    else:
        import core.users as users
        access = acl.AccessData(user=users.getUser('Gast')) 
        
    oaisets.loadGroups() 
    SET_LIST = oaisets.GROUPS
    
    OUT('OAI: initSetList: found %s set groups: %s' %(len(SET_LIST), str(SET_LIST)))  
     
    if DEBUG: timetable_update(req, "leaving initSetList")     
    
def oaiRequest(req):
    import time
    
    start_time = time.clock()
    req._tt = {'atime': now(), 'tlist':[]}
    req.request["Content-Type"] = "text/xml"
    
    if "until" in req.params:
        try:
            date_to = parseDate(req.params.get("until"))
        except:
            writeHead(req, "noatt")
            writeError(req, "badArgument", "badDateformatUntil")
            writeTail(req)
            return

    elif "from" in req.params:
        try:
            date_from = parseDate(req.params.get("from"))
        except:
            writeHead(req, "noatt")
            writeError(req, "badArgument", "badDateformatFrom")
            writeTail(req)
            return

    if "verb" not in req.params:
        writeHead(req, "noatt")
        writeError(req,"badVerb")
        
    else:
        verb = req.params.get("verb")
        if verb=="Identify":
            writeHead(req)
            Identify(req)
        elif verb=="ListMetadataFormats":
            writeHead(req)
            ListMetadataFormats(req)
        elif verb=="ListSets":
            writeHead(req)
            ListSets(req)
        elif verb=="ListIdentifiers":
            writeHead(req)
            ListIdentifiers(req)
        elif verb=="ListRecords":
            writeHead(req)
            ListRecords(req)
        elif verb=="GetRecord":
            writeHead(req)
            GetRecord(req)
        else:
            writeHead(req, "noatt")
            writeError(req,"badVerb")

    writeTail(req)
    
    useragent = 'unknown'
    try:
        cutoff = 60
        useragent = req.request_headers['user-agent']
        if len(useragent) > cutoff:    
            useragent = useragent[0:cutoff]+'...'
    except:
        pass  
        
    exit_time = now() 
    
    OUT("%s:%d OAI (exit after %.3f sec.) %s - (user-agent: %s)" % (req.ip, req.channel.addr[1], (exit_time-start_time), (req.path + req.uri).replace('//','/'), useragent))
    
    if DEBUG: OUT(timetable_string(req))
    
