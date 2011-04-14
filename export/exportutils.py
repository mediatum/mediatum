"""
 mediatum - a multimedia content repository

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

import re, sys
import core
import core.tree as tree
from schema.schema import getMetadataType
from core.athana import *
from utils.utils import esc, u

tagpattern = re.compile(r'<[^>]*?>')

def no_html(s):
    return tagpattern.sub('', s)
    
# source: http://www.programmierer-forum.de/x80-x82-x84-x95-x96-x97-usw-in-utf8-wandeln-t114493.htm#2074995
trans_table= {
"\xc2\x80": "\xE2\x82\xAC", # EURO SIGN
"\xc2\x82": "\xE2\x80\x9A",	# SINGLE LOW-9 QUOTATION MARK
"\xc2\x83": "\xC6\x92",	# LATIN SMALL LETTER F WITH HOOK
"\xc2\x84": "\xE2\x80\x9E",	# DOUBLE LOW-9 QUOTATION MARK
"\xc2\x85": "\xE2\x80\xA6",	# HORIZONTAL ELLIPSIS
"\xc2\x86": "\xE2\x80\xA0",	# DAGGER
"\xc2\x87": "\xE2\x80\xA1",	# DOUBLE DAGGER
"\xc2\x88": "\xCB\x86", # MODIFIER LETTER CIRCUMFLEX ACCENT
"\xc2\x89": "\xE2\x80\xB0",	# PER MILLE SIGN
"\xc2\x8A": "\xC5\xA0", # LATIN CAPITAL LETTER S WITH CARON
"\xc2\x8B": "\xE2\x80\xB9",	# SINGLE LEFT-POINTING ANGLE QUOTATION MARK
"\xc2\x8C": "\xC5\x92", # LATIN CAPITAL LIGATURE OE
"\xc2\x8E": "\xC5\xBD",	# LATIN CAPITAL LETTER Z WITH CARON
"\xc2\x91": "\xE2\x80\x98",	# LEFT SINGLE QUOTATION MARK
"\xc2\x92": "\xE2\x80\x99",	# RIGHT SINGLE QUOTATION MARK
"\xc2\x93": "\xE2\x80\x9C",	# LEFT DOUBLE QUOTATION MARK
"\xc2\x94": "\xE2\x80\x9D",	# RIGHT DOUBLE QUOTATION MARK
"\xc2\x95": "\xE2\x80\xA2",	# BULLET
"\xc2\x96": "\xE2\x80\x93",	# EN DASH
"\xc2\x97": "\xE2\x80\x94",	# EM DASH
"\xc2\x98": "\xCB\x9C",	# SMALL TILDE
"\xc2\x99": "\xE2\x84\xA2",	# TRADE MARK SIGN
"\xc2\x9A": "\xC5\xA1", # LATIN SMALL LETTER S WITH CARON
"\xc2\x9B": "\xE2\x80\xBA",	# SINGLE RIGHT-POINTING ANGLE QUOTATION MARK
"\xc2\x9C": "\xC5\x93", # LATIN SMALL LIGATURE OE
"\xc2\x9E": "\xC5\xBE", # LATIN SMALL LETTER Z WITH CARON
"\xc2\x9F": "\xC5\xB8",	# LATIN CAPITAL LETTER Y WITH DIAERESIS
"&euro;": "\xE2\x82\xAC", # EURO SIGN

# 'title' of node 1071645
"\x0b": "",
"\x0c": "",
"\x7f": "",

}
 
def no_amp(s):
    s = u(s)
    for k, v in trans_table.items():
        s = s.replace(u(k), u(v))
    return s.replace("&", "[AMP]")   
    
def prss(s):
    '''protect rss item elements'''
    return no_amp(no_html(esc(no_html(u(s)))))    

def parseArgString(s):

    def delimiterError():
        msg = "delimiter error: " + str(s)
        print "SytaxError:", msg
        raise SyntaxError(msg)

    s = s.strip()
    if len(s)>=2:
        erg = []
        delimiter = s[0]
        delimitercount = s.count(delimiter)
        if (delimitercount % 2) or (delimiter != s[-1]):
            delimiterError()
        count = delimitercount / 2
        if count == 1:
            erg = [ (s[1:-1], ) ] # list of tuples
        if count >= 2:
            pattern = '%s([^%s]*)%s[ \t]*' + ',[ \t]*%s([^%s]*)%s[ \t]*'*(count - 1)
            erg = re.findall(pattern % tuple([delimiter]*3*count), s)
        if len(erg) != 1:
            delimiterError()
        return erg[0]

def translate(v, arg):
    ipos = arg.index(v)
    translated = ''
    if ipos >= 0 and ipos < len(arg)-1:
        translated = arg[ipos + 1]
    return translated

def runTALSnippet(s, context, mask):
    import core

    import cStringIO
    buffer = cStringIO.StringIO()

    p = core.athana.TALParser(TALGenerator(AthanaTALEngine()))

    header = '''\
<?xml version="1.0" encoding="UTF-8" ?>
'''
    header += mask.get('exportheader')

    xmlns = '''\
<talnamespaces
    xmlns:tal="http://xml.zope.org/namespaces/tal"
    xmlns:metal="http://xml.zope.org/namespaces/metal">
'''

    footer = '</talnamespaces>' + mask.get('exportfooter')
    cutter ="----cut-TAL-result-here----"
    to_be_processed = header + xmlns + cutter + s + cutter + footer

    p.parseString(to_be_processed)
    program, macros = p.getCode()
    engine = AthanaTALEngine(macros, context)
    TALInterpreter(program, macros, engine, buffer, wrap=0)()
    wr_result = buffer.getvalue()
    return wr_result[wr_result.find(cutter)+len(cutter):wr_result.rfind(cutter)]


def handleCommand(cmd, var, s, node, attrnode=None, field_value="", options=[], mask=None):

    argString = var[len( cmd + "(" ):var.rfind(")")]
    arglist = []
    if argString:
        arglist = list(parseArgString(argString))

    if cmd == 'cmd:translate':
        v = getMetadataType(attrnode.getFieldtype()).getFormatedValue(attrnode, node)[1]
        if v=="":
            v = node.get(attrnode.getName())
        if v:
            v = translate(v, arglist)
        else:
            v = ''

        if "t" in options and not v.isdigit():
            v = '"' + v + '"'
        return s.replace("[" + var + "]", v)


    if cmd == 'cmd:translateAttr':
        v = ''
        if arglist:
            print 2, arglist
            v = node.get(arglist[0])
            if len(arglist) > 1:
                v = translate(v, arglist[1:])
        print 3, v
        if "t" in options and not v.isdigit():
            v = '"' + v + '"'
        return s.replace("[" + var + "]", v)


    if cmd == 'cmd:loopSplitted':
        v = getMetadataType(attrnode.getFieldtype()).getFormatedValue(attrnode, node)[1]
        if v=="":
            v = node.get(attrnode.getName())

        v_list = v.split(arglist[0])
        v_list = [x.strip() for x in v_list]

        result = ""
        for v in v_list:
            if "t" in options and not v.isdigit():
                v = '"' + v + '"'
            result += (s.replace("[" + var + "]", v) + arglist[1])

        s = result
        return s

        
    if cmd == 'cmd:loopSplittedAttribute':
        #v = getMetadataType(attrnode.getFieldtype()).getFormatedValue(attrnode, node)[1]
        #if v=="":
        #    v = node.get(attrnode.getName())
        v = node.get(arglist[0])

        v_list = v.split(arglist[1])
        v_list = [x.strip() for x in v_list]

        result = ""
        for v in v_list:
            if "t" in options and not v.isdigit():
                v = '"' + v + '"'
            result += (s.replace("[" + var + "]", v) + arglist[2])

        s = result
        return s


    if cmd == 'cmd:loopDissContributors':
        result = ""
        arg = arglist[0]

        if arg in ["advisor", "referee"]:
            from utils.utils import splitname

            v = node.get(arg)
            for person in v.split(";"):
                if person:
                    cfullname=person.strip()
                    title,firstname,lastname = splitname(cfullname)
                    type = arg
                    result += ( (s % locals()) + "\n")

            s = result.replace("[" + var + "]", "")
        return s

        
    if cmd == 'cmd:getFileCount':
        arg = arglist[0]
        filecount = len([f for f in node.getFiles() if f.getType().find(arg) >= 0])
        return s.replace("[" + var + "]", "%d" % filecount)


    if cmd == 'cmd:loopFiles':
        arg = arglist[0]
        result = ""
        mimetype = ""
        filesize = 0
        fileid = "node"+node.id
        filename = ""

        for file in node.getFiles():

            if file.getType().find(arg) >= 0:
                mimetype = file.getMimeType()
                filesize = file.getSize()
                filename = file.getName()
                result += ( (s % locals()) + "\n")

        return result.replace("[" + var + "]", "")

        
    if cmd == 'cmd:readItemsDict':
        dict_items = dict(node.items())

        #not all metadata for this type may be set
        metadatatype = core.tree.getRoot('metadatatypes').getChild(node.getSchema())
        metafields = [cn.name for cn in metadatatype.getChildren() if cn.type=='metafield']

        for mf in metafields:
            if not mf in dict_items.keys():
                dict_items[mf] = ''

        result = s % dict_items
        return result.replace("[" + var + "]", "")


    if cmd == 'cmd:getTAL':
        context = dict(node.items())
        # not all metafields may have values
        # default behavior should be taken care of in the TAL

        context['tree'] = tree
        context['node'] = node
        context['esc'] = esc  # may be needed for example in escaping rss item elements
        context['no_html'] = no_html 
        context['u'] = u 
        context['no_amp'] = no_amp
        context['prss'] = prss # protect rss

        result = runTALSnippet(s, context, mask)

        return result.replace("[" + var + "]", "")
