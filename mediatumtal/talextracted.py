# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import print_function

import logging

logg = logging.getLogger("mediatumtal")

GLOBAL_ROOT_DIR = ""

class TALError(Exception):

    def __init__(self, msg, position=(None, None)):
        assert msg != ""
        self.msg = msg
        self.lineno = position[0]
        self.offset = position[1]
        self.filename = None

    def setFile(self, filename):
        self.filename = filename

    def __str__(self):
        result = self.msg
        if self.lineno is not None:
            result = result + ", at line %d" % self.lineno
        if self.offset is not None:
            result = result + ", column %d" % (self.offset + 1)
        if self.filename is not None:
            result = result + ', in file %s' % self.filename
        return result

class METALError(TALError):
    pass

class TALESError(TALError):
    pass

class I18NError(TALError):
    pass

import sys

from HTMLParser import HTMLParser, HTMLParseError

BOOLEAN_HTML_ATTRS = [
    "compact", "nowrap", "ismap", "declare", "noshade", "checked",
    "disabled", "readonly", "multiple", "selected", "noresize",
    "defer"
    ]

EMPTY_HTML_TAGS = [
    "base", "meta", "link", "hr", "br", "param", "img", "area",
    "input", "col", "basefont", "isindex", "frame",
    ]

PARA_LEVEL_HTML_TAGS = [
    "h1", "h2", "h3", "h4", "h5", "h6", "p",
    ]

BLOCK_CLOSING_TAG_MAP = {
    "tr": ("tr", "td", "th"),
    "td": ("td", "th"),
    "th": ("td", "th"),
    "li": ("li",),
    "dd": ("dd", "dt"),
    "dt": ("dd", "dt"),
    }

BLOCK_LEVEL_HTML_TAGS = [
    "blockquote", "table", "tr", "th", "td", "thead", "tfoot", "tbody",
    "noframe", "ul", "ol", "li", "dl", "dt", "dd", "div",
    ]

TIGHTEN_IMPLICIT_CLOSE_TAGS = (PARA_LEVEL_HTML_TAGS
                               + BLOCK_CLOSING_TAG_MAP.keys())


class NestingError(HTMLParseError):
    """Exception raised when elements aren't properly nested."""

    def __init__(self, tagstack, endtag, position=(None, None)):
        self.endtag = endtag
        if tagstack:
            if len(tagstack) == 1:
                msg = ('Open tag <%s> does not match close tag </%s>'
                       % (tagstack[0], endtag))
            else:
                msg = ('Open tags <%s> do not match close tag </%s>'
                       % ('>, <'.join(tagstack), endtag))
        else:
            msg = 'No tags are open to match </%s>' % endtag
        HTMLParseError.__init__(self, msg, position)

class EmptyTagError(NestingError):
    """Exception raised when empty elements have an end tag."""

    def __init__(self, tag, position=(None, None)):
        self.tag = tag
        msg = 'Close tag </%s> should be removed' % tag
        HTMLParseError.__init__(self, msg, position)

class OpenTagError(NestingError):
    """Exception raised when a tag is not allowed in another tag."""

    def __init__(self, tagstack, tag, position=(None, None)):
        self.tag = tag
        msg = 'Tag <%s> is not allowed in <%s>' % (tag, tagstack[-1])
        HTMLParseError.__init__(self, msg, position)

class HTMLTALParser(HTMLParser):


    def __init__(self, gen=None):
        HTMLParser.__init__(self)
        if gen is None:
            gen = TALGenerator(xml=0)
        self.gen = gen
        self.tagstack = []
        self.nsstack = []
        self.nsdict = {'tal': ZOPE_TAL_NS,
                       'metal': ZOPE_METAL_NS,
                       'i18n': ZOPE_I18N_NS,
                       }

    def parseFile(self, file):
        f = open(file)
        data = f.read()
        f.close()
        try:
            self.parseString(data)
        except TALError as e:
            e.setFile(file)
            raise

    def parseString(self, data):
        self.feed(data)
        self.close()
        while self.tagstack:
            self.implied_endtag(self.tagstack[-1], 2)
        assert self.nsstack == [], self.nsstack

    def getCode(self):
        return self.gen.getCode()

    def getWarnings(self):
        return ()


    def handle_starttag(self, tag, attrs):
        self.close_para_tags(tag)
        self.scan_xmlns(attrs)
        tag, attrlist, taldict, metaldict, i18ndict \
             = self.process_ns(tag, attrs)
        if tag in EMPTY_HTML_TAGS and taldict.get("content"):
            raise TALError(
                "empty HTML tags cannot use tal:content: %s" % `tag`,
                self.getpos())
        self.tagstack.append(tag)
        self.gen.emitStartElement(tag, attrlist, taldict, metaldict, i18ndict,
                                  self.getpos())
        if tag in EMPTY_HTML_TAGS:
            self.implied_endtag(tag, -1)

    def handle_startendtag(self, tag, attrs):
        self.close_para_tags(tag)
        self.scan_xmlns(attrs)
        tag, attrlist, taldict, metaldict, i18ndict \
             = self.process_ns(tag, attrs)
        if taldict.get("content"):
            if tag in EMPTY_HTML_TAGS:
                raise TALError(
                    "empty HTML tags cannot use tal:content: %s" % `tag`,
                    self.getpos())
            self.gen.emitStartElement(tag, attrlist, taldict, metaldict,
                                      i18ndict, self.getpos())
            self.gen.emitEndElement(tag, implied=-1)
        else:
            self.gen.emitStartElement(tag, attrlist, taldict, metaldict,
                                      i18ndict, self.getpos(), isend=1)
        self.pop_xmlns()

    def handle_endtag(self, tag):
        if tag in EMPTY_HTML_TAGS:
            raise EmptyTagError(tag, self.getpos())
        self.close_enclosed_tags(tag)
        self.gen.emitEndElement(tag)
        self.pop_xmlns()
        self.tagstack.pop()

    def close_para_tags(self, tag):
        if tag in EMPTY_HTML_TAGS:
            return
        close_to = -1
        if tag in BLOCK_CLOSING_TAG_MAP:
            blocks_to_close = BLOCK_CLOSING_TAG_MAP[tag]
            for i in range(len(self.tagstack)):
                t = self.tagstack[i]
                if t in blocks_to_close:
                    if close_to == -1:
                        close_to = i
                elif t in BLOCK_LEVEL_HTML_TAGS:
                    close_to = -1
        elif tag in PARA_LEVEL_HTML_TAGS + BLOCK_LEVEL_HTML_TAGS:
            i = len(self.tagstack) - 1
            while i >= 0:
                closetag = self.tagstack[i]
                if closetag in BLOCK_LEVEL_HTML_TAGS:
                    break
                if closetag in PARA_LEVEL_HTML_TAGS:
                    if closetag != "p":
                        raise OpenTagError(self.tagstack, tag, self.getpos())
                    close_to = i
                i = i - 1
        if close_to >= 0:
            while len(self.tagstack) > close_to:
                self.implied_endtag(self.tagstack[-1], 1)

    def close_enclosed_tags(self, tag):
        if tag not in self.tagstack:
            raise NestingError(self.tagstack, tag, self.getpos())
        while tag != self.tagstack[-1]:
            self.implied_endtag(self.tagstack[-1], 1)
        assert self.tagstack[-1] == tag

    def implied_endtag(self, tag, implied):
        assert tag == self.tagstack[-1]
        assert implied in (-1, 1, 2)
        isend = (implied < 0)
        if tag in TIGHTEN_IMPLICIT_CLOSE_TAGS:
            white = self.gen.unEmitWhitespace()
        else:
            white = None
        self.gen.emitEndElement(tag, isend=isend, implied=implied)
        if white:
            self.gen.emitRawText(white)
        self.tagstack.pop()
        self.pop_xmlns()

    def handle_charref(self, name):
        self.gen.emitRawText("&#%s;" % name)

    def handle_entityref(self, name):
        self.gen.emitRawText("&%s;" % name)

    def handle_data(self, data):
        self.gen.emitRawText(data)

    def handle_comment(self, data):
        self.gen.emitRawText("<!--%s-->" % data)

    def handle_decl(self, data):
        self.gen.emitRawText("<!%s>" % data)

    def handle_pi(self, data):
        self.gen.emitRawText("<?%s>" % data)


    def scan_xmlns(self, attrs):
        nsnew = {}
        for key, value in attrs:
            if key.startswith("xmlns:"):
                nsnew[key[6:]] = value
        if nsnew:
            self.nsstack.append(self.nsdict)
            self.nsdict = self.nsdict.copy()
            self.nsdict.update(nsnew)
        else:
            self.nsstack.append(self.nsdict)

    def pop_xmlns(self):
        self.nsdict = self.nsstack.pop()

    def fixname(self, name):
        if ':' in name:
            prefix, suffix = name.split(':', 1)
            if prefix == 'xmlns':
                nsuri = self.nsdict.get(suffix)
                if nsuri in (ZOPE_TAL_NS, ZOPE_METAL_NS, ZOPE_I18N_NS):
                    return name, name, prefix
            else:
                nsuri = self.nsdict.get(prefix)
                if nsuri == ZOPE_TAL_NS:
                    return name, suffix, 'tal'
                elif nsuri == ZOPE_METAL_NS:
                    return name, suffix,  'metal'
                elif nsuri == ZOPE_I18N_NS:
                    return name, suffix, 'i18n'
        return name, name, 0

    def process_ns(self, name, attrs):
        attrlist = []
        taldict = {}
        metaldict = {}
        i18ndict = {}
        name, namebase, namens = self.fixname(name)
        for item in attrs:
            key, value = item
            key, keybase, keyns = self.fixname(key)
            ns = keyns or namens # default to tag namespace
            if ns and ns != 'unknown':
                item = (key, value, ns)
            if ns == 'tal':
                if keybase in taldict:
                    raise TALError("duplicate TAL attribute " +
                                   `keybase`, self.getpos())
                taldict[keybase] = value
            elif ns == 'metal':
                if keybase in metaldict:
                    raise METALError("duplicate METAL attribute " +
                                     `keybase`, self.getpos())
                metaldict[keybase] = value
            elif ns == 'i18n':
                if keybase in i18ndict:
                    raise I18NError("duplicate i18n attribute " +
                                    `keybase`, self.getpos())
                i18ndict[keybase] = value
            attrlist.append(item)
        if namens in ('metal', 'tal'):
            taldict['tal tag'] = namens
        return name, attrlist, taldict, metaldict, i18ndict
"""
Generic expat-based XML parser base class.
"""


class XMLParser:

    ordered_attributes = 0

    handler_names = [
        "StartElementHandler",
        "EndElementHandler",
        "ProcessingInstructionHandler",
        "CharacterDataHandler",
        "UnparsedEntityDeclHandler",
        "NotationDeclHandler",
        "StartNamespaceDeclHandler",
        "EndNamespaceDeclHandler",
        "CommentHandler",
        "StartCdataSectionHandler",
        "EndCdataSectionHandler",
        "DefaultHandler",
        "DefaultHandlerExpand",
        "NotStandaloneHandler",
        "ExternalEntityRefHandler",
        "XmlDeclHandler",
        "StartDoctypeDeclHandler",
        "EndDoctypeDeclHandler",
        "ElementDeclHandler",
        "AttlistDeclHandler"
        ]

    def __init__(self, encoding=None):
        self.parser = p = self.createParser()
        if self.ordered_attributes:
            try:
                self.parser.ordered_attributes = self.ordered_attributes
            except AttributeError:
                logg.debug("Can't set ordered_attributes")
                self.ordered_attributes = 0
        for name in self.handler_names:
            method = getattr(self, name, None)
            if method is not None:
                try:
                    setattr(p, name, method)
                except AttributeError:
                    logg.debug("Can't set expat handler %s", name)

    def createParser(self, encoding=None):
        global XMLParseError
        from xml.parsers import expat
        XMLParseError = expat.ExpatError
        return expat.ParserCreate(encoding, ' ')

    def parseFile(self, filename):
        f = open(filename)
        self.parseStream(f)
        #self.parseStream(open(filename))

    def parseString(self, s):
        self.parser.Parse(s, 1)

    def parseURL(self, url):
        import urllib
        self.parseStream(urllib.urlopen(url))

    def parseStream(self, stream):
        self.parser.ParseFile(stream)

    def parseFragment(self, s, end=0):
        self.parser.Parse(s, end)
"""Interface that a TALES engine provides to the METAL/TAL implementation."""

try:
    from Interface import Interface
    from Interface.Attribute import Attribute
except:
    class Interface: pass
    def Attribute(*args): pass


class ITALESCompiler(Interface):
    """Compile-time interface provided by a TALES implementation.

    The TAL compiler needs an instance of this interface to support
    compilation of TALES expressions embedded in documents containing
    TAL and METAL constructs.
    """

    def getCompilerError():
        """Return the exception class raised for compilation errors.
        """

    def compile(expression):
        """Return a compiled form of 'expression' for later evaluation.

        'expression' is the source text of the expression.

        The return value may be passed to the various evaluate*()
        methods of the ITALESEngine interface.  No compatibility is
        required for the values of the compiled expression between
        different ITALESEngine implementations.
        """


class ITALESEngine(Interface):
    """Render-time interface provided by a TALES implementation.

    The TAL interpreter uses this interface to TALES to support
    evaluation of the compiled expressions returned by
    ITALESCompiler.compile().
    """

    def getCompiler():
        """Return an object that supports ITALESCompiler."""

    def getDefault():
        """Return the value of the 'default' TALES expression.

        Checking a value for a match with 'default' should be done
        using the 'is' operator in Python.
        """

    def setPosition((lineno, offset)):
        """Inform the engine of the current position in the source file.

        This is used to allow the evaluation engine to report
        execution errors so that site developers can more easily
        locate the offending expression.
        """

    def setSourceFile(filename):
        """Inform the engine of the name of the current source file.

        This is used to allow the evaluation engine to report
        execution errors so that site developers can more easily
        locate the offending expression.
        """

    def beginScope():
        """Push a new scope onto the stack of open scopes.
        """

    def endScope():
        """Pop one scope from the stack of open scopes.
        """

    def evaluate(compiled_expression):
        """Evaluate an arbitrary expression.

        No constraints are imposed on the return value.
        """

    def evaluateBoolean(compiled_expression):
        """Evaluate an expression that must return a Boolean value.
        """

    def evaluateMacro(compiled_expression):
        """Evaluate an expression that must return a macro program.
        """

    def evaluateStructure(compiled_expression):
        """Evaluate an expression that must return a structured
        document fragment.

        The result of evaluating 'compiled_expression' must be a
        string containing a parsable HTML or XML fragment.  Any TAL
        markup cnotained in the result string will be interpreted.
        """

    def evaluateText(compiled_expression):
        """Evaluate an expression that must return text.

        The returned text should be suitable for direct inclusion in
        the output: any HTML or XML escaping or quoting is the
        responsibility of the expression itself.
        """

    def evaluateValue(compiled_expression):
        """Evaluate an arbitrary expression.

        No constraints are imposed on the return value.
        """

    def createErrorInfo(exception, (lineno, offset)):
        """Returns an ITALESErrorInfo object.

        The returned object is used to provide information about the
        error condition for the on-error handler.
        """

    def setGlobal(name, value):
        """Set a global variable.

        The variable will be named 'name' and have the value 'value'.
        """

    def setLocal(name, value):
        """Set a local variable in the current scope.

        The variable will be named 'name' and have the value 'value'.
        """

    def setRepeat(name, compiled_expression):
        """
        """

    def translate(domain, msgid, mapping, default=None):
        """
        See ITranslationService.translate()
        """


class ITALESErrorInfo(Interface):

    type = Attribute("type",
                     "The exception class.")

    value = Attribute("value",
                      "The exception instance.")

    lineno = Attribute("lineno",
                       "The line number the error occurred on in the source.")

    offset = Attribute("offset",
                       "The character offset at which the error occurred.")
"""
Common definitions used by TAL and METAL compilation an transformation.
"""

from types import ListType, TupleType


TAL_VERSION = "1.5"

XML_NS = "http://www.w3.org/XML/1998/namespace" # URI for XML namespace
XMLNS_NS = "http://www.w3.org/2000/xmlns/" # URI for XML NS declarations

ZOPE_TAL_NS = "http://xml.zope.org/namespaces/tal"
ZOPE_METAL_NS = "http://xml.zope.org/namespaces/metal"
ZOPE_I18N_NS = "http://xml.zope.org/namespaces/i18n"

NAME_RE = "[a-zA-Z_][-a-zA-Z0-9_]*"

KNOWN_METAL_ATTRIBUTES = [
    "define-macro",
    "use-macro",
    "define-slot",
    "fill-slot",
    "slot",
    ]

KNOWN_TAL_ATTRIBUTES = [
    "define",
    "condition",
    "content",
    "replace",
    "repeat",
    "attributes",
    "on-error",
    "omit-tag",
    "tal tag",
    ]

KNOWN_I18N_ATTRIBUTES = [
    "translate",
    "domain",
    "target",
    "source",
    "attributes",
    "data",
    "name",
    ]

class ErrorInfo:

    __implements__ = ITALESErrorInfo

    def __init__(self, err, position=(None, None)):
        if isinstance(err, Exception):
            self.type = err.__class__
            self.value = err
        else:
            self.type = err
            self.value = None
        self.lineno = position[0]
        self.offset = position[1]



import re
_attr_re = re.compile(r"\s*([^\s]+)\s+([^\s].*)\Z", re.S)
_subst_re = re.compile(r"\s*(?:(text|raw|structure)\s+)?(.*)\Z", re.S)
del re

def parseAttributeReplacements(arg, xml):
    dict = {}
    for part in splitParts(arg):
        m = _attr_re.match(part)
        if not m:
            raise TALError("Bad syntax in attributes: " + `part`)
        name, expr = m.group(1, 2)
        if not xml:
            name = name.lower()
        if name in dict:
            raise TALError("Duplicate attribute name in attributes: " + `part`)
        dict[name] = expr
    return dict

def parseSubstitution(arg, position=(None, None)):
    m = _subst_re.match(arg)
    if not m:
        raise TALError("Bad syntax in substitution text: " + `arg`, position)
    key, expr = m.group(1, 2)
    if not key:
        key = "text"
    return key, expr

def splitParts(arg):
    arg = arg.replace(";;", "\0")
    parts = arg.split(';')
    parts = [p.replace("\0", ";") for p in parts]
    if len(parts) > 1 and not parts[-1].strip():
        del parts[-1] # It ended in a semicolon
    return parts

def isCurrentVersion(program):
    version = getProgramVersion(program)
    return version == TAL_VERSION

def getProgramMode(program):
    version = getProgramVersion(program)
    if (version == TAL_VERSION and isinstance(program[1], TupleType) and
        len(program[1]) == 2):
        opcode, mode = program[1]
        if opcode == "mode":
            return mode
    return None

def getProgramVersion(program):
    if (len(program) >= 2 and
        isinstance(program[0], TupleType) and len(program[0]) == 2):
        opcode, version = program[0]
        if opcode == "version":
            return version
    return None

import re
_ent1_re = re.compile('&(?![A-Z#])', re.I)
_entch_re = re.compile('&([A-Z][A-Z0-9]*)(?![A-Z0-9;])', re.I)
_entn1_re = re.compile('&#(?![0-9X])', re.I)
_entnx_re = re.compile('&(#X[A-F0-9]*)(?![A-F0-9;])', re.I)
_entnd_re = re.compile('&(#[0-9][0-9]*)(?![0-9;])')
del re

def attrEscape(s):
    """Replace special characters '&<>' by character entities,
    except when '&' already begins a syntactically valid entity."""
    s = _ent1_re.sub('&amp;', s)
    s = _entch_re.sub(r'&amp;\1', s)
    s = _entn1_re.sub('&amp;#', s)
    s = _entnx_re.sub(r'&amp;\1', s)
    s = _entnd_re.sub(r'&amp;\1', s)
    s = s.replace('<', '&lt;')
    s = s.replace('>', '&gt;')
    s = s.replace('"', '&quot;')
    return s
"""
Code generator for TALInterpreter intermediate code.
"""

import re
import cgi



I18N_REPLACE = 1
I18N_CONTENT = 2
I18N_EXPRESSION = 3

_name_rx = re.compile(NAME_RE)


class TALGenerator:

    inMacroUse = 0
    inMacroDef = 0
    source_file = None

    def __init__(self, expressionCompiler=None, xml=1, source_file=None):
        if not expressionCompiler:
            expressionCompiler = AthanaTALEngine()
        self.expressionCompiler = expressionCompiler
        self.CompilerError = expressionCompiler.getCompilerError()
        self.program = []
        self.stack = []
        self.todoStack = []
        self.macros = {}
        self.slots = {}
        self.slotStack = []
        self.xml = xml
        self.emit("version", TAL_VERSION)
        self.emit("mode", xml and "xml" or "html")
        if source_file is not None:
            self.source_file = source_file
            self.emit("setSourceFile", source_file)
        self.i18nContext = TranslationContext()
        self.i18nLevel = 0

    def getCode(self):
        assert not self.stack
        assert not self.todoStack
        return self.optimize(self.program), self.macros

    def optimize(self, program):
        output = []
        collect = []
        cursor = 0
        if self.xml:
            endsep = "/>"
        else:
            endsep = " />"
        for cursor in xrange(len(program)+1):
            try:
                item = program[cursor]
            except IndexError:
                item = (None, None)
            opcode = item[0]
            if opcode == "rawtext":
                collect.append(item[1])
                continue
            if opcode == "endTag":
                collect.append("</%s>" % item[1])
                continue
            if opcode == "startTag":
                if self.optimizeStartTag(collect, item[1], item[2], ">"):
                    continue
            if opcode == "startEndTag":
                if self.optimizeStartTag(collect, item[1], item[2], endsep):
                    continue
            if opcode in ("beginScope", "endScope"):
                output.append(self.optimizeArgsList(item))
                continue
            if opcode == 'noop':
                opcode = None
                pass
            text = "".join(collect)
            if text:
                i = text.rfind("\n")
                if i >= 0:
                    i = len(text) - (i + 1)
                    output.append(("rawtextColumn", (text, i)))
                else:
                    output.append(("rawtextOffset", (text, len(text))))
            if opcode != None:
                output.append(self.optimizeArgsList(item))
            collect = []
        return self.optimizeCommonTriple(output)

    def optimizeArgsList(self, item):
        if len(item) == 2:
            return item
        else:
            return item[0], tuple(item[1:])

    def optimizeStartTag(self, collect, name, attrlist, end):
        if not attrlist:
            collect.append("<%s%s" % (name, end))
            return 1
        opt = 1
        new = ["<" + name]
        for i in range(len(attrlist)):
            item = attrlist[i]
            if len(item) > 2:
                opt = 0
                name, value, action = item[:3]
                attrlist[i] = (name, value, action) + item[3:]
            else:
                if item[1] is None:
                    s = item[0]
                else:
                    s = '%s="%s"' % (item[0], attrEscape(item[1]))
                attrlist[i] = item[0], s
                new.append(" " + s)
        if opt:
            new.append(end)
            collect.extend(new)
        return opt

    def optimizeCommonTriple(self, program):
        if len(program) < 3:
            return program
        output = program[:2]
        prev2, prev1 = output
        for item in program[2:]:
            if ( item[0] == "beginScope"
                 and prev1[0] == "setPosition"
                 and prev2[0] == "rawtextColumn"):
                position = output.pop()[1]
                text, column = output.pop()[1]
                prev1 = None, None
                closeprev = 0
                if output and output[-1][0] == "endScope":
                    closeprev = 1
                    output.pop()
                item = ("rawtextBeginScope",
                        (text, column, position, closeprev, item[1]))
            output.append(item)
            prev2 = prev1
            prev1 = item
        return output

    def todoPush(self, todo):
        self.todoStack.append(todo)

    def todoPop(self):
        return self.todoStack.pop()

    def compileExpression(self, expr):
        try:
            return self.expressionCompiler.compile(expr)
        except self.CompilerError as err:
            raise TALError('%s in expression %s' % (err.args[0], `expr`),
                           self.position)

    def pushProgram(self):
        self.stack.append(self.program)
        self.program = []

    def popProgram(self):
        program = self.program
        self.program = self.stack.pop()
        return self.optimize(program)

    def pushSlots(self):
        self.slotStack.append(self.slots)
        self.slots = {}

    def popSlots(self):
        slots = self.slots
        self.slots = self.slotStack.pop()
        return slots

    def emit(self, *instruction):
        self.program.append(instruction)

    def emitStartTag(self, name, attrlist, isend=0):
        if isend:
            opcode = "startEndTag"
        else:
            opcode = "startTag"
        self.emit(opcode, name, attrlist)

    def emitEndTag(self, name):
        if self.xml and self.program and self.program[-1][0] == "startTag":
            self.program[-1] = ("startEndTag",) + self.program[-1][1:]
        else:
            self.emit("endTag", name)

    def emitOptTag(self, name, optTag, isend):
        program = self.popProgram() #block
        start = self.popProgram() #start tag
        if (isend or not program) and self.xml:
            start[-1] = ("startEndTag",) + start[-1][1:]
            isend = 1
        cexpr = optTag[0]
        if cexpr:
            cexpr = self.compileExpression(optTag[0])
        self.emit("optTag", name, cexpr, optTag[1], isend, start, program)

    def emitRawText(self, text):
        self.emit("rawtext", text)

    def emitText(self, text):
        self.emitRawText(cgi.escape(text))

    def emitDefines(self, defines):
        for part in splitParts(defines):
            m = re.match(
                r"(?s)\s*(?:(global|local)\s+)?(%s)\s+(.*)\Z" % NAME_RE, part)
            if not m:
                raise TALError("invalid define syntax: " + `part`,
                               self.position)
            scope, name, expr = m.group(1, 2, 3)
            scope = scope or "local"
            cexpr = self.compileExpression(expr)
            if scope == "local":
                self.emit("setLocal", name, cexpr)
            else:
                self.emit("setGlobal", name, cexpr)

    def emitOnError(self, name, onError, TALtag, isend):
        block = self.popProgram()
        key, expr = parseSubstitution(onError)
        cexpr = self.compileExpression(expr)
        if key == "text":
            self.emit("insertText", cexpr, [])
        elif key == "raw":
            self.emit("insertRaw", cexpr, [])
        else:
            assert key == "structure"
            self.emit("insertStructure", cexpr, {}, [])
        if TALtag:
            self.emitOptTag(name, (None, 1), isend)
        else:
            self.emitEndTag(name)
        handler = self.popProgram()
        self.emit("onError", block, handler)

    def emitCondition(self, expr):
        cexpr = self.compileExpression(expr)
        program = self.popProgram()
        self.emit("condition", cexpr, program)

    def emitRepeat(self, arg):


        m = re.match("(?s)\s*(%s)\s+(.*)\Z" % NAME_RE, arg)
        if not m:
            raise TALError("invalid repeat syntax: " + `arg`,
                           self.position)
        name, expr = m.group(1, 2)
        cexpr = self.compileExpression(expr)
        program = self.popProgram()
        self.emit("loop", name, cexpr, program)


    def emitSubstitution(self, arg, attrDict={}):
        key, expr = parseSubstitution(arg)
        cexpr = self.compileExpression(expr)
        program = self.popProgram()
        if key == "text":
            self.emit("insertText", cexpr, program)
        elif key == "raw":
            self.emit("insertRaw", cexpr, program)
        else:
            assert key == "structure"
            self.emit("insertStructure", cexpr, attrDict, program)

    def emitI18nVariable(self, stuff):
        varname, action, expression = stuff
        m = _name_rx.match(varname)
        if m is None or m.group() != varname:
            raise TALError("illegal i18n:name: %r" % varname, self.position)
        key = cexpr = None
        program = self.popProgram()
        if action == I18N_REPLACE:
            program = program[1:-1]
        elif action == I18N_CONTENT:
            pass
        else:
            assert action == I18N_EXPRESSION
            key, expr = parseSubstitution(expression)
            cexpr = self.compileExpression(expr)
        self.emit('i18nVariable',
                  varname, program, cexpr, int(key == "structure"))

    def emitTranslation(self, msgid, i18ndata):
        program = self.popProgram()
        if i18ndata is None:
            self.emit('insertTranslation', msgid, program)
        else:
            key, expr = parseSubstitution(i18ndata)
            cexpr = self.compileExpression(expr)
            assert key == 'text'
            self.emit('insertTranslation', msgid, program, cexpr)

    def emitDefineMacro(self, macroName):
        program = self.popProgram()
        macroName = macroName.strip()
        if macroName in self.macros:
            raise METALError("duplicate macro definition: %s" % `macroName`,
                             self.position)
        if not re.match('%s$' % NAME_RE, macroName):
            raise METALError("invalid macro name: %s" % `macroName`,
                             self.position)
        self.macros[macroName] = program
        self.inMacroDef = self.inMacroDef - 1
        self.emit("defineMacro", macroName, program)

    def emitUseMacro(self, expr):
        cexpr = self.compileExpression(expr)
        program = self.popProgram()
        self.inMacroUse = 0
        self.emit("useMacro", expr, cexpr, self.popSlots(), program)

    def emitDefineSlot(self, slotName):
        program = self.popProgram()
        slotName = slotName.strip()
        if not re.match('%s$' % NAME_RE, slotName):
            raise METALError("invalid slot name: %s" % `slotName`,
                             self.position)
        self.emit("defineSlot", slotName, program)

    def emitFillSlot(self, slotName):
        program = self.popProgram()
        slotName = slotName.strip()
        if self.slots.has_key(slotName):
            raise METALError("duplicate fill-slot name: %s" % `slotName`,
                             self.position)
        if not re.match('%s$' % NAME_RE, slotName):
            raise METALError("invalid slot name: %s" % `slotName`,
                             self.position)
        self.slots[slotName] = program
        self.inMacroUse = 1
        self.emit("fillSlot", slotName, program)

    def unEmitWhitespace(self):
        collect = []
        i = len(self.program) - 1
        while i >= 0:
            item = self.program[i]
            if item[0] != "rawtext":
                break
            text = item[1]
            if not re.match(r"\A\s*\Z", text):
                break
            collect.append(text)
            i = i-1
        del self.program[i+1:]
        if i >= 0 and self.program[i][0] == "rawtext":
            text = self.program[i][1]
            m = re.search(r"\s+\Z", text)
            if m:
                self.program[i] = ("rawtext", text[:m.start()])
                collect.append(m.group())
        collect.reverse()
        return "".join(collect)

    def unEmitNewlineWhitespace(self):
        collect = []
        i = len(self.program)
        while i > 0:
            i = i-1
            item = self.program[i]
            if item[0] != "rawtext":
                break
            text = item[1]
            if re.match(r"\A[ \t]*\Z", text):
                collect.append(text)
                continue
            m = re.match(r"(?s)^(.*)(\n[ \t]*)\Z", text)
            if not m:
                break
            text, rest = m.group(1, 2)
            collect.reverse()
            rest = rest + "".join(collect)
            del self.program[i:]
            if text:
                self.emit("rawtext", text)
            return rest
        return None

    def replaceAttrs(self, attrlist, repldict):
        if not repldict:
            return attrlist
        newlist = []
        for item in attrlist:
            key = item[0]
            if key in repldict:
                expr, xlat, msgid = repldict[key]
                item = item[:2] + ("replace", expr, xlat, msgid)
                del repldict[key]
            newlist.append(item)
        for key, (expr, xlat, msgid) in repldict.items():
            newlist.append((key, None, "insert", expr, xlat, msgid))
        return newlist

    def emitStartElement(self, name, attrlist, taldict, metaldict, i18ndict,
                         position=(None, None), isend=0):
        if not taldict and not metaldict and not i18ndict:
            self.emitStartTag(name, attrlist, isend)
            self.todoPush({})
            if isend:
                self.emitEndElement(name, isend)
            return

        self.position = position
        for key, value in taldict.items():
            if key not in KNOWN_TAL_ATTRIBUTES:
                raise TALError("bad TAL attribute: " + `key`, position)
            if not (value or key == 'omit-tag'):
                raise TALError("missing value for TAL attribute: " +
                               `key`, position)
        for key, value in metaldict.items():
            if key not in KNOWN_METAL_ATTRIBUTES:
                raise METALError("bad METAL attribute: " + `key`,
                                 position)
            if not value:
                raise TALError("missing value for METAL attribute: " +
                               `key`, position)
        for key, value in i18ndict.items():
            if key not in KNOWN_I18N_ATTRIBUTES:
                raise I18NError("bad i18n attribute: " + `key`, position)
            if not value and key in ("attributes", "data", "id"):
                raise I18NError("missing value for i18n attribute: " +
                                `key`, position)
        todo = {}
        defineMacro = metaldict.get("define-macro")
        useMacro = metaldict.get("use-macro")
        defineSlot = metaldict.get("define-slot")
        fillSlot = metaldict.get("fill-slot")
        define = taldict.get("define")
        condition = taldict.get("condition")
        repeat = taldict.get("repeat")
        content = taldict.get("content")
        replace = taldict.get("replace")
        attrsubst = taldict.get("attributes")
        onError = taldict.get("on-error")
        omitTag = taldict.get("omit-tag")
        TALtag = taldict.get("tal tag")
        i18nattrs = i18ndict.get("attributes")
        msgid = i18ndict.get("translate")
        varname = i18ndict.get('name')
        i18ndata = i18ndict.get('data')

        if varname and not self.i18nLevel:
            raise I18NError(
                "i18n:name can only occur inside a translation unit",
                position)

        if i18ndata and not msgid:
            raise I18NError("i18n:data must be accompanied by i18n:translate",
                            position)

        if len(metaldict) > 1 and (defineMacro or useMacro):
            raise METALError("define-macro and use-macro cannot be used "
                             "together or with define-slot or fill-slot",
                             position)
        if replace:
            if content:
                raise TALError(
                    "tal:content and tal:replace are mutually exclusive",
                    position)
            if msgid is not None:
                raise I18NError(
                    "i18n:translate and tal:replace are mutually exclusive",
                    position)

        repeatWhitespace = None
        if repeat:
            repeatWhitespace = self.unEmitNewlineWhitespace()
        if position != (None, None):
            self.emit("setPosition", position)
        if self.inMacroUse:
            if fillSlot:
                self.pushProgram()
                if self.source_file is not None:
                    self.emit("setSourceFile", self.source_file)
                todo["fillSlot"] = fillSlot
                self.inMacroUse = 0
        else:
            if fillSlot:
                raise METALError("fill-slot must be within a use-macro",
                                 position)
        if not self.inMacroUse:
            if defineMacro:
                self.pushProgram()
                self.emit("version", TAL_VERSION)
                self.emit("mode", self.xml and "xml" or "html")
                if self.source_file is not None:
                    self.emit("setSourceFile", self.source_file)
                todo["defineMacro"] = defineMacro
                self.inMacroDef = self.inMacroDef + 1
            if useMacro:
                self.pushSlots()
                self.pushProgram()
                todo["useMacro"] = useMacro
                self.inMacroUse = 1
            if defineSlot:
                if not self.inMacroDef:
                    raise METALError(
                        "define-slot must be within a define-macro",
                        position)
                self.pushProgram()
                todo["defineSlot"] = defineSlot

        if defineSlot or i18ndict:

            domain = i18ndict.get("domain") or self.i18nContext.domain
            source = i18ndict.get("source") or self.i18nContext.source
            target = i18ndict.get("target") or self.i18nContext.target
            if (  domain != DEFAULT_DOMAIN
                  or source is not None
                  or target is not None):
                self.i18nContext = TranslationContext(self.i18nContext,
                                                      domain=domain,
                                                      source=source,
                                                      target=target)
                self.emit("beginI18nContext",
                          {"domain": domain, "source": source,
                           "target": target})
                todo["i18ncontext"] = 1
        if taldict or i18ndict:
            dict = {}
            for item in attrlist:
                key, value = item[:2]
                dict[key] = value
            self.emit("beginScope", dict)
            todo["scope"] = 1
        if onError:
            self.pushProgram() # handler
            if TALtag:
                self.pushProgram() # start
            self.emitStartTag(name, list(attrlist)) # Must copy attrlist!
            if TALtag:
                self.pushProgram() # start
            self.pushProgram() # block
            todo["onError"] = onError
        if define:
            self.emitDefines(define)
            todo["define"] = define
        if condition:
            self.pushProgram()
            todo["condition"] = condition
        if repeat:
            todo["repeat"] = repeat
            self.pushProgram()
            if repeatWhitespace:
                self.emitText(repeatWhitespace)
        if content:
            if varname:
                todo['i18nvar'] = (varname, I18N_CONTENT, None)
                todo["content"] = content
                self.pushProgram()
            else:
                todo["content"] = content
        elif replace:
            if varname:
                todo['i18nvar'] = (varname, I18N_EXPRESSION, replace)
            else:
                todo["replace"] = replace
            self.pushProgram()
        elif varname:
            todo['i18nvar'] = (varname, I18N_REPLACE, None)
            self.pushProgram()
        if msgid is not None:
            self.i18nLevel += 1
            todo['msgid'] = msgid
        if i18ndata:
            todo['i18ndata'] = i18ndata
        optTag = omitTag is not None or TALtag
        if optTag:
            todo["optional tag"] = omitTag, TALtag
            self.pushProgram()
        if attrsubst or i18nattrs:
            if attrsubst:
                repldict = parseAttributeReplacements(attrsubst,
                                                              self.xml)
            else:
                repldict = {}
            if i18nattrs:
                i18nattrs = _parseI18nAttributes(i18nattrs, attrlist, repldict,
                                                 self.position, self.xml,
                                                 self.source_file)
            else:
                i18nattrs = {}
            for key, value in repldict.items():
                if i18nattrs.get(key, None):
                    raise I18NError(
                      ("attribute [%s] cannot both be part of tal:attributes" +
                      " and have a msgid in i18n:attributes") % key,
                    position)
                ce = self.compileExpression(value)
                repldict[key] = ce, key in i18nattrs, i18nattrs.get(key)
            for key in i18nattrs:
                if not key in repldict:
                    repldict[key] = None, 1, i18nattrs.get(key)
        else:
            repldict = {}
        if replace:
            todo["repldict"] = repldict
            repldict = {}
        self.emitStartTag(name, self.replaceAttrs(attrlist, repldict), isend)
        if optTag:
            self.pushProgram()
        if content and not varname:
            self.pushProgram()
        if msgid is not None:
            self.pushProgram()
        if content and varname:
            self.pushProgram()
        if todo and position != (None, None):
            todo["position"] = position
        self.todoPush(todo)
        if isend:
            self.emitEndElement(name, isend)

    def emitEndElement(self, name, isend=0, implied=0):
        todo = self.todoPop()
        if not todo:
            if not isend:
                self.emitEndTag(name)
            return

        self.position = position = todo.get("position", (None, None))
        defineMacro = todo.get("defineMacro")
        useMacro = todo.get("useMacro")
        defineSlot = todo.get("defineSlot")
        fillSlot = todo.get("fillSlot")
        repeat = todo.get("repeat")
        content = todo.get("content")
        replace = todo.get("replace")
        condition = todo.get("condition")
        onError = todo.get("onError")
        repldict = todo.get("repldict", {})
        scope = todo.get("scope")
        optTag = todo.get("optional tag")
        msgid = todo.get('msgid')
        i18ncontext = todo.get("i18ncontext")
        varname = todo.get('i18nvar')
        i18ndata = todo.get('i18ndata')

        if implied > 0:
            if defineMacro or useMacro or defineSlot or fillSlot:
                exc = METALError
                what = "METAL"
            else:
                exc = TALError
                what = "TAL"
            raise exc("%s attributes on <%s> require explicit </%s>" %
                      (what, name, name), position)

        if content:
            self.emitSubstitution(content, {})
        if msgid is not None:
            if (not varname) or (
                varname and (varname[1] == I18N_CONTENT)):
                self.emitTranslation(msgid, i18ndata)
            self.i18nLevel -= 1
        if optTag:
            self.emitOptTag(name, optTag, isend)
        elif not isend:
            if varname:
                self.emit('noop')
            self.emitEndTag(name)
        if replace:
            self.emitSubstitution(replace, repldict)
        elif varname:
            assert (varname[1]
                    in [I18N_REPLACE, I18N_CONTENT, I18N_EXPRESSION])
            self.emitI18nVariable(varname)
        if msgid is not None:
            if varname and (varname[1] <> I18N_CONTENT):
                self.emitTranslation(msgid, i18ndata)
        if repeat:
            self.emitRepeat(repeat)
        if condition:
            self.emitCondition(condition)
        if onError:
            self.emitOnError(name, onError, optTag and optTag[1], isend)
        if scope:
            self.emit("endScope")
        if i18ncontext:
            self.emit("endI18nContext")
            assert self.i18nContext.parent is not None
            self.i18nContext = self.i18nContext.parent
        if defineSlot:
            self.emitDefineSlot(defineSlot)
        if fillSlot:
            self.emitFillSlot(fillSlot)
        if useMacro:
            self.emitUseMacro(useMacro)
        if defineMacro:
            self.emitDefineMacro(defineMacro)

def _parseI18nAttributes(i18nattrs, attrlist, repldict, position,
                         xml, source_file):

    def addAttribute(dic, attr, msgid, position, xml):
        if not xml:
            attr = attr.lower()
        if attr in dic:
            raise TALError(
                "attribute may only be specified once in i18n:attributes: "
                + attr,
                position)
        dic[attr] = msgid

    d = {}
    if ';' in i18nattrs:
        i18nattrlist = i18nattrs.split(';')
        i18nattrlist = [attr.strip().split()
                        for attr in i18nattrlist if attr.strip()]
        for parts in i18nattrlist:
            if len(parts) > 2:
                raise TALError("illegal i18n:attributes specification: %r"
                                % parts, position)
            if len(parts) == 2:
                attr, msgid = parts
            else:
                attr = parts[0]
                msgid = None
            addAttribute(d, attr, msgid, position, xml)
    else:
        i18nattrlist = i18nattrs.split()
        if len(i18nattrlist) == 1:
            addAttribute(d, i18nattrlist[0], None, position, xml)
        elif len(i18nattrlist) == 2:
            staticattrs = [attr[0] for attr in attrlist if len(attr) == 2]
            if (not i18nattrlist[1] in staticattrs) and (
                not i18nattrlist[1] in repldict):
                attr, msgid = i18nattrlist
                addAttribute(d, attr, msgid, position, xml)
            else:
                import warnings
                warnings.warn(I18N_ATTRIBUTES_WARNING
                % (source_file, str(position), i18nattrs)
                , DeprecationWarning)
                msgid = None
                for attr in i18nattrlist:
                    addAttribute(d, attr, msgid, position, xml)
        else:
            import warnings
            warnings.warn(I18N_ATTRIBUTES_WARNING
            % (source_file, str(position), i18nattrs)
            , DeprecationWarning)
            msgid = None
            for attr in i18nattrlist:
                addAttribute(d, attr, msgid, position, xml)
    return d

I18N_ATTRIBUTES_WARNING = (
    'Space separated attributes in i18n:attributes'
    ' are deprecated (i18n:attributes="value title"). Please use'
    ' semicolon to separate attributes'
    ' (i18n:attributes="value; title").'
    '\nFile %s at row, column %s\nAttributes %s')

"""Interpreter for a pre-compiled TAL program.

"""
import cgi
import sys
import getopt
import re
from cgi import escape

from StringIO import StringIO



class ConflictError:
    pass

class MessageID:
    pass



BOOLEAN_HTML_ATTRS = [
    "compact", "nowrap", "ismap", "declare", "noshade", "checked",
    "disabled", "readonly", "multiple", "selected", "noresize",
    "defer"
]

def _init():
    d = {}
    for s in BOOLEAN_HTML_ATTRS:
        d[s] = 1
    return d

BOOLEAN_HTML_ATTRS = _init()

_nulljoin = ''.join
_spacejoin = ' '.join

def normalize(text):
    return _spacejoin(text.split())


NAME_RE = r"[a-zA-Z][a-zA-Z0-9_]*"
_interp_regex = re.compile(r'(?<!\$)(\$(?:%(n)s|{%(n)s}))' %({'n': NAME_RE}))
_get_var_regex = re.compile(r'%(n)s' %({'n': NAME_RE}))

def interpolate(text, mapping):
    """Interpolate ${keyword} substitutions.

    This is called when no translation is provided by the translation
    service.
    """
    if not mapping:
        return text
    to_replace = _interp_regex.findall(text)
    for string in to_replace:
        var = _get_var_regex.findall(string)[0]
        if mapping.has_key(var):
            subst = str(mapping[var])
            try:
                text = text.replace(string, subst)
            except UnicodeError:
                subst = `subst`[1:-1]
                text = text.replace(string, subst)
    return text


class AltTALGenerator(TALGenerator):

    def __init__(self, repldict, expressionCompiler=None, xml=0):
        self.repldict = repldict
        self.enabled = 1
        TALGenerator.__init__(self, expressionCompiler, xml)

    def enable(self, enabled):
        self.enabled = enabled

    def emit(self, *args):
        if self.enabled:
            TALGenerator.emit(self, *args)

    def emitStartElement(self, name, attrlist, taldict, metaldict, i18ndict,
                         position=(None, None), isend=0):
        metaldict = {}
        taldict = {}
        i18ndict = {}
        if self.enabled and self.repldict:
            taldict["attributes"] = "x x"
        TALGenerator.emitStartElement(self, name, attrlist,
                                      taldict, metaldict, i18ndict,
                                      position, isend)

    def replaceAttrs(self, attrlist, repldict):
        if self.enabled and self.repldict:
            repldict = self.repldict
            self.repldict = None
        return TALGenerator.replaceAttrs(self, attrlist, repldict)


class TALInterpreter:

    def __init__(self, program, macros, engine, stream=None,
                 debug=0, wrap=60, metal=1, tal=1, showtal=-1,
                 strictinsert=1, stackLimit=100, i18nInterpolate=1):
        self.program = program
        self.macros = macros
        self.engine = engine # Execution engine (aka context)
        self.Default = engine.getDefault()
        self.stream = stream or sys.stdout
        self._stream_write = self.stream.write
        self.debug = debug
        self.wrap = wrap
        self.metal = metal
        self.tal = tal
        if tal:
            self.dispatch = self.bytecode_handlers_tal
        else:
            self.dispatch = self.bytecode_handlers
        assert showtal in (-1, 0, 1)
        if showtal == -1:
            showtal = (not tal)
        self.showtal = showtal
        self.strictinsert = strictinsert
        self.stackLimit = stackLimit
        self.html = 0
        self.endsep = "/>"
        self.endlen = len(self.endsep)
        self.macroStack = []
        self.position = None, None  # (lineno, offset)
        self.col = 0
        self.level = 0
        self.scopeLevel = 0
        self.sourceFile = None
        self.i18nStack = []
        self.i18nInterpolate = i18nInterpolate
        self.i18nContext = TranslationContext()

    def StringIO(self):
        return FasterStringIO()

    def saveState(self):
        return (self.position, self.col, self.stream,
                self.scopeLevel, self.level, self.i18nContext)

    def restoreState(self, state):
        (self.position, self.col, self.stream,
         scopeLevel, level, i18n) = state
        self._stream_write = self.stream.write
        assert self.level == level
        while self.scopeLevel > scopeLevel:
            self.engine.endScope()
            self.scopeLevel = self.scopeLevel - 1
        self.engine.setPosition(self.position)
        self.i18nContext = i18n

    def restoreOutputState(self, state):
        (dummy, self.col, self.stream,
         scopeLevel, level, i18n) = state
        self._stream_write = self.stream.write
        assert self.level == level
        assert self.scopeLevel == scopeLevel

    def pushMacro(self, macroName, slots, entering=1):
        if len(self.macroStack) >= self.stackLimit:
            raise METALError("macro nesting limit (%d) exceeded "
                             "by %s" % (self.stackLimit, `macroName`))
        self.macroStack.append([macroName, slots, entering, self.i18nContext])

    def popMacro(self):
        return self.macroStack.pop()

    def __call__(self):
        assert self.level == 0
        assert self.scopeLevel == 0
        assert self.i18nContext.parent is None
        self.interpret(self.program)
        assert self.level == 0
        assert self.scopeLevel == 0
        assert self.i18nContext.parent is None
        if self.col > 0:
            self._stream_write("\n")
            self.col = 0

    def interpretWithStream(self, program, stream):
        oldstream = self.stream
        self.stream = stream
        self._stream_write = stream.write
        try:
            self.interpret(program)
        finally:
            self.stream = oldstream
            self._stream_write = oldstream.write

    def stream_write(self, s,
                     len=len):
        self._stream_write(s)
        i = s.rfind('\n')
        if i < 0:
            self.col = self.col + len(s)
        else:
            self.col = len(s) - (i + 1)

    bytecode_handlers = {}

    def interpret(self, program):
        oldlevel = self.level
        self.level = oldlevel + 1
        handlers = self.dispatch
        try:
            if self.debug:
                for (opcode, args) in program:
                    s = "%sdo_%s(%s)\n" % ("    "*self.level, opcode,
                                           repr(args))
                    if len(s) > 80:
                        s = s[:76] + "...\n"
                    sys.stderr.write(s)
                    handlers[opcode](self, args)
            else:
                for (opcode, args) in program:
                    handlers[opcode](self, args)
        finally:
            self.level = oldlevel

    def do_version(self, version):
        assert version == TAL_VERSION
    bytecode_handlers["version"] = do_version

    def do_mode(self, mode):
        assert mode in ("html", "xml")
        self.html = (mode == "html")
        if self.html:
            self.endsep = " />"
        else:
            self.endsep = "/>"
        self.endlen = len(self.endsep)
    bytecode_handlers["mode"] = do_mode

    def do_setSourceFile(self, source_file):
        self.sourceFile = source_file
        self.engine.setSourceFile(source_file)
    bytecode_handlers["setSourceFile"] = do_setSourceFile

    def do_setPosition(self, position):
        self.position = position
        self.engine.setPosition(position)
    bytecode_handlers["setPosition"] = do_setPosition

    def do_startEndTag(self, stuff):
        self.do_startTag(stuff, self.endsep, self.endlen)
    bytecode_handlers["startEndTag"] = do_startEndTag

    def do_startTag(self, (name, attrList),
                    end=">", endlen=1, _len=len):
        self._currentTag = name
        L = ["<", name]
        append = L.append
        col = self.col + _len(name) + 1
        wrap = self.wrap
        align = col + 1
        if align >= wrap//2:
            align = 4  # Avoid a narrow column far to the right
        attrAction = self.dispatch["<attrAction>"]
        try:
            for item in attrList:
                if _len(item) == 2:
                    name, s = item
                else:
                    if item[2] in ('metal', 'tal', 'xmlns', 'i18n'):
                        if not self.showtal:
                            continue
                        ok, name, s = self.attrAction(item)
                    else:
                        ok, name, s = attrAction(self, item)
                    if not ok:
                        continue
                slen = _len(s)
                if (wrap and
                    col >= align and
                    col + 1 + slen > wrap):
                    append("\n")
                    append(" "*align)
                    col = align + slen
                else:
                    append(" ")
                    col = col + 1 + slen
                append(s)
            append(end)
            col = col + endlen
        finally:
            self._stream_write(_nulljoin(L))
            self.col = col
    bytecode_handlers["startTag"] = do_startTag

    def attrAction(self, item):
        name, value, action = item[:3]
        if action == 'insert':
            return 0, name, value
        macs = self.macroStack
        if action == 'metal' and self.metal and macs:
            if len(macs) > 1 or not macs[-1][2]:
                return 0, name, value
            macs[-1][2] = 0
            i = name.rfind(":") + 1
            prefix, suffix = name[:i], name[i:]
            if suffix == "define-macro":
                name = prefix + "use-macro"
                value = macs[-1][0] # Macro name
            elif suffix == "define-slot":
                name = prefix + "fill-slot"
            elif suffix == "fill-slot":
                pass
            else:
                return 0, name, value

        if value is None:
            value = name
        else:
            value = '%s="%s"' % (name, attrEscape(value))
        return 1, name, value

    def attrAction_tal(self, item):
        name, value, action = item[:3]
        ok = 1
        expr, xlat, msgid = item[3:]
        if self.html and name.lower() in BOOLEAN_HTML_ATTRS:
            evalue = self.engine.evaluateBoolean(item[3])
            if evalue is self.Default:
                if action == 'insert': # Cancelled insert
                    ok = 0
            elif evalue:
                value = None
            else:
                ok = 0
        elif expr is not None:
            evalue = self.engine.evaluateText(item[3])
            if evalue is self.Default:
                if action == 'insert': # Cancelled insert
                    ok = 0
            else:
                if evalue is None:
                    ok = 0
                value = evalue
        else:
            evalue = None

        if ok:
            if xlat:
                translated = self.translate(msgid or value, value, {})
                if translated is not None:
                    value = translated
            if value is None:
                value = name
            elif evalue is self.Default:
                value = attrEscape(value)
            else:
                value = escape(value, quote=1)
            value = '%s="%s"' % (name, value)
        return ok, name, value
    bytecode_handlers["<attrAction>"] = attrAction

    def no_tag(self, start, program):
        state = self.saveState()
        self.stream = stream = self.StringIO()
        self._stream_write = stream.write
        self.interpret(start)
        self.restoreOutputState(state)
        self.interpret(program)

    def do_optTag(self, (name, cexpr, tag_ns, isend, start, program),
                  omit=0):
        if tag_ns and not self.showtal:
            return self.no_tag(start, program)

        self.interpret(start)
        if not isend:
            self.interpret(program)
            s = '</%s>' % name
            self._stream_write(s)
            self.col = self.col + len(s)

    def do_optTag_tal(self, stuff):
        cexpr = stuff[1]
        if cexpr is not None and (cexpr == '' or
                                  self.engine.evaluateBoolean(cexpr)):
            self.no_tag(stuff[-2], stuff[-1])
        else:
            self.do_optTag(stuff)
    bytecode_handlers["optTag"] = do_optTag

    def do_rawtextBeginScope(self, (s, col, position, closeprev, dict)):
        self._stream_write(s)
        self.col = col
        self.position = position
        self.engine.setPosition(position)
        if closeprev:
            engine = self.engine
            engine.endScope()
            engine.beginScope()
        else:
            self.engine.beginScope()
            self.scopeLevel = self.scopeLevel + 1

    def do_rawtextBeginScope_tal(self, (s, col, position, closeprev, dict)):
        self._stream_write(s)
        self.col = col
        engine = self.engine
        self.position = position
        engine.setPosition(position)
        if closeprev:
            engine.endScope()
            engine.beginScope()
        else:
            engine.beginScope()
            self.scopeLevel = self.scopeLevel + 1
        engine.setLocal("attrs", dict)
    bytecode_handlers["rawtextBeginScope"] = do_rawtextBeginScope

    def do_beginScope(self, dict):
        self.engine.beginScope()
        self.scopeLevel = self.scopeLevel + 1

    def do_beginScope_tal(self, dict):
        engine = self.engine
        engine.beginScope()
        engine.setLocal("attrs", dict)
        self.scopeLevel = self.scopeLevel + 1
    bytecode_handlers["beginScope"] = do_beginScope

    def do_endScope(self, notused=None):
        self.engine.endScope()
        self.scopeLevel = self.scopeLevel - 1
    bytecode_handlers["endScope"] = do_endScope

    def do_setLocal(self, notused):
        pass

    def do_setLocal_tal(self, (name, expr)):
        self.engine.setLocal(name, self.engine.evaluateValue(expr))
    bytecode_handlers["setLocal"] = do_setLocal

    def do_setGlobal_tal(self, (name, expr)):
        self.engine.setGlobal(name, self.engine.evaluateValue(expr))
    bytecode_handlers["setGlobal"] = do_setLocal

    def do_beginI18nContext(self, settings):
        get = settings.get
        self.i18nContext = TranslationContext(self.i18nContext,
                                              domain=get("domain"),
                                              source=get("source"),
                                              target=get("target"))
    bytecode_handlers["beginI18nContext"] = do_beginI18nContext

    def do_endI18nContext(self, notused=None):
        self.i18nContext = self.i18nContext.parent
        assert self.i18nContext is not None
    bytecode_handlers["endI18nContext"] = do_endI18nContext

    def do_insertText(self, stuff):
        self.interpret(stuff[1])

    def do_insertText_tal(self, stuff):
        text = self.engine.evaluateText(stuff[0])
        if text is None:
            return
        if text is self.Default:
            self.interpret(stuff[1])
            return
        if isinstance(text, MessageID):
            text = self.engine.translate(text.domain, text, text.mapping)
        s = escape(text)
        self._stream_write(s)
        i = s.rfind('\n')
        if i < 0:
            self.col = self.col + len(s)
        else:
            self.col = len(s) - (i + 1)
    bytecode_handlers["insertText"] = do_insertText

    def do_insertRawText_tal(self, stuff):
        text = self.engine.evaluateText(stuff[0])
        if text is None:
            return
        if text is self.Default:
            self.interpret(stuff[1])
            return
        if isinstance(text, MessageID):
            text = self.engine.translate(text.domain, text, text.mapping)
        s = text
        self._stream_write(s)
        i = s.rfind('\n')
        if i < 0:
            self.col = self.col + len(s)
        else:
            self.col = len(s) - (i + 1)

    def do_i18nVariable(self, stuff):
        varname, program, expression, structure = stuff
        if expression is None:
            state = self.saveState()
            try:
                tmpstream = self.StringIO()
                self.interpretWithStream(program, tmpstream)
                if self.html and self._currentTag == "pre":
                    value = tmpstream.getvalue()
                else:
                    value = normalize(tmpstream.getvalue())
            finally:
                self.restoreState(state)
        else:
            if structure:
                value = self.engine.evaluateStructure(expression)
            else:
                value = self.engine.evaluate(expression)

            if isinstance(value, MessageID):
                value = self.engine.translate(value.domain, value,
                                              value.mapping)

            if not structure:
                value = cgi.escape(str(value))

        i18ndict, srepr = self.i18nStack[-1]
        i18ndict[varname] = value
        placeholder = '${%s}' % varname
        srepr.append(placeholder)
        self._stream_write(placeholder)
    bytecode_handlers['i18nVariable'] = do_i18nVariable

    def do_insertTranslation(self, stuff):
        i18ndict = {}
        srepr = []
        obj = None
        self.i18nStack.append((i18ndict, srepr))
        msgid = stuff[0]
        currentTag = self._currentTag
        tmpstream = self.StringIO()
        self.interpretWithStream(stuff[1], tmpstream)
        default = tmpstream.getvalue()
        if not msgid:
            if self.html and currentTag == "pre":
                msgid = default
            else:
                msgid = normalize(default)
        self.i18nStack.pop()
        if len(stuff) > 2:
            obj = self.engine.evaluate(stuff[2])
        xlated_msgid = self.translate(msgid, default, i18ndict, obj)
        assert xlated_msgid is not None
        self._stream_write(xlated_msgid)
    bytecode_handlers['insertTranslation'] = do_insertTranslation

    def do_insertStructure(self, stuff):
        self.interpret(stuff[2])

    def do_insertStructure_tal(self, (expr, repldict, block)):
        structure = self.engine.evaluateStructure(expr)
        if structure is None:
            return
        if structure is self.Default:
            self.interpret(block)
            return
        if isinstance(structure, str):
            text = structure.decode("utf8")
        else:
            text = unicode(structure)
        if not (repldict or self.strictinsert):
            self.stream_write(text)
            return
        if self.html:
            self.insertHTMLStructure(text, repldict)
        else:
            self.insertXMLStructure(text, repldict)
    bytecode_handlers["insertStructure"] = do_insertStructure

    def insertHTMLStructure(self, text, repldict):
        gen = AltTALGenerator(repldict, self.engine.getCompiler(), 0)
        p = HTMLTALParser(gen) # Raises an exception if text is invalid
        p.parseString(text)
        program, macros = p.getCode()
        self.interpret(program)

    def insertXMLStructure(self, text, repldict):
        gen = AltTALGenerator(repldict, self.engine.getCompiler(), 0)
        p = TALParser(gen)
        gen.enable(0)
        p.parseFragment('<!DOCTYPE foo PUBLIC "foo" "bar"><foo>')
        gen.enable(1)
        p.parseFragment(text.encode("utf8")) # Raises an exception if text is invalid
        gen.enable(0)
        p.parseFragment('</foo>', 1)
        program, macros = gen.getCode()
        self.interpret(program)

    def do_loop(self, (name, expr, block)):
        self.interpret(block)

    def do_loop_tal(self, (name, expr, block)):
        iterator = self.engine.setRepeat(name, expr)
        while iterator.next():
            self.interpret(block)
    bytecode_handlers["loop"] = do_loop

    def translate(self, msgid, default, i18ndict, obj=None):
        if obj:
            i18ndict.update(obj)
        if not self.i18nInterpolate:
            return msgid
        return self.engine.translate(self.i18nContext.domain,
                                     msgid, i18ndict, default=default)

    def do_rawtextColumn(self, (s, col)):
        self._stream_write(s)
        self.col = col
    bytecode_handlers["rawtextColumn"] = do_rawtextColumn

    def do_rawtextOffset(self, (s, offset)):
        self._stream_write(s)
        self.col = self.col + offset
    bytecode_handlers["rawtextOffset"] = do_rawtextOffset

    def do_condition(self, (condition, block)):
        if not self.tal or self.engine.evaluateBoolean(condition):
            self.interpret(block)
    bytecode_handlers["condition"] = do_condition

    def do_defineMacro(self, (macroName, macro)):
        macs = self.macroStack
        if len(macs) == 1:
            entering = macs[-1][2]
            if not entering:
                macs.append(None)
                self.interpret(macro)
                assert macs[-1] is None
                macs.pop()
                return
        self.interpret(macro)
    bytecode_handlers["defineMacro"] = do_defineMacro

    def do_useMacro(self, (macroName, macroExpr, compiledSlots, block)):
        if not self.metal:
            self.interpret(block)
            return
        macro = self.engine.evaluateMacro(macroExpr)
        if macro is self.Default:
            macro = block
        else:
            if not isCurrentVersion(macro):
                raise METALError("macro %s has incompatible version %s" %
                                 (`macroName`, `getProgramVersion(macro)`),
                                 self.position)
            mode = getProgramMode(macro)
            #if mode != (self.html and "html" or "xml"):
            #    raise METALError("macro %s has incompatible mode %s" %
            #                     (`macroName`, `mode`), self.position)

        self.pushMacro(macroName, compiledSlots)
        prev_source = self.sourceFile
        self.interpret(macro)
        if self.sourceFile != prev_source:
            self.engine.setSourceFile(prev_source)
            self.sourceFile = prev_source
        self.popMacro()
    bytecode_handlers["useMacro"] = do_useMacro

    def do_fillSlot(self, (slotName, block)):
        self.interpret(block)
    bytecode_handlers["fillSlot"] = do_fillSlot

    def do_defineSlot(self, (slotName, block)):
        if not self.metal:
            self.interpret(block)
            return
        macs = self.macroStack
        if macs and macs[-1] is not None:
            macroName, slots = self.popMacro()[:2]
            slot = slots.get(slotName)
            if slot is not None:
                prev_source = self.sourceFile
                self.interpret(slot)
                if self.sourceFile != prev_source:
                    self.engine.setSourceFile(prev_source)
                    self.sourceFile = prev_source
                self.pushMacro(macroName, slots, entering=0)
                return
            self.pushMacro(macroName, slots)
        self.interpret(block)
    bytecode_handlers["defineSlot"] = do_defineSlot

    def do_onError(self, (block, handler)):
        self.interpret(block)

    def do_onError_tal(self, (block, handler)):
        state = self.saveState()
        self.stream = stream = self.StringIO()
        self._stream_write = stream.write
        try:
            self.interpret(block)
        except ConflictError:
            raise
        except:
            exc = sys.exc_info()[1]
            self.restoreState(state)
            engine = self.engine
            engine.beginScope()
            error = engine.createErrorInfo(exc, self.position)
            engine.setLocal('error', error)
            try:
                self.interpret(handler)
            finally:
                engine.endScope()
        else:
            self.restoreOutputState(state)
            self.stream_write(stream.getvalue())
    bytecode_handlers["onError"] = do_onError

    bytecode_handlers_tal = bytecode_handlers.copy()
    bytecode_handlers_tal["rawtextBeginScope"] = do_rawtextBeginScope_tal
    bytecode_handlers_tal["beginScope"] = do_beginScope_tal
    bytecode_handlers_tal["setLocal"] = do_setLocal_tal
    bytecode_handlers_tal["setGlobal"] = do_setGlobal_tal
    bytecode_handlers_tal["insertStructure"] = do_insertStructure_tal
    bytecode_handlers_tal["insertText"] = do_insertText_tal
    bytecode_handlers_tal["insertRaw"] = do_insertRawText_tal
    bytecode_handlers_tal["loop"] = do_loop_tal
    bytecode_handlers_tal["onError"] = do_onError_tal
    bytecode_handlers_tal["<attrAction>"] = attrAction_tal
    bytecode_handlers_tal["optTag"] = do_optTag_tal


class FasterStringIO(StringIO):
    """Append-only version of StringIO.

    This let's us have a much faster write() method.
    """
    def close(self):
        if not self.closed:
            self.write = _write_ValueError
            StringIO.close(self)

    def seek(self, pos, mode=0):
        raise RuntimeError("FasterStringIO.seek() not allowed")

    def write(self, s):
        self.buflist.append(s)
        self.len = self.pos = self.pos + len(s)


def _write_ValueError(s):
    raise ValueError, "I/O operation on closed file"
"""
Parse XML and compile to TALInterpreter intermediate code.
"""


class TALParser(XMLParser):

    ordered_attributes = 1

    def __init__(self, gen=None): # Override
        XMLParser.__init__(self)
        if gen is None:
            gen = TALGenerator()
        self.gen = gen
        self.nsStack = []
        self.nsDict = {XML_NS: 'xml'}
        self.nsNew = []

    def getCode(self):
        return self.gen.getCode()

    def getWarnings(self):
        return ()

    def StartNamespaceDeclHandler(self, prefix, uri):
        self.nsStack.append(self.nsDict.copy())
        self.nsDict[uri] = prefix
        self.nsNew.append((prefix, uri))

    def EndNamespaceDeclHandler(self, prefix):
        self.nsDict = self.nsStack.pop()

    def StartElementHandler(self, name, attrs):
        if self.ordered_attributes:
            attrlist = []
            for i in range(0, len(attrs), 2):
                key = attrs[i]
                value = attrs[i+1]
                attrlist.append((key, value))
        else:
            attrlist = attrs.items()
            attrlist.sort() # For definiteness
        name, attrlist, taldict, metaldict, i18ndict \
              = self.process_ns(name, attrlist)
        attrlist = self.xmlnsattrs() + attrlist
        self.gen.emitStartElement(name, attrlist, taldict, metaldict, i18ndict)

    def process_ns(self, name, attrlist):
        taldict = {}
        metaldict = {}
        i18ndict = {}
        fixedattrlist = []
        name, namebase, namens = self.fixname(name)
        for key, value in attrlist:
            key, keybase, keyns = self.fixname(key)
            ns = keyns or namens # default to tag namespace
            item = key, value
            if ns == 'metal':
                metaldict[keybase] = value
                item = item + ("metal",)
            elif ns == 'tal':
                taldict[keybase] = value
                item = item + ("tal",)
            elif ns == 'i18n':
                i18ndict[keybase] = value
                item = item + ('i18n',)
            fixedattrlist.append(item)
        if namens in ('metal', 'tal', 'i18n'):
            taldict['tal tag'] = namens
        return name, fixedattrlist, taldict, metaldict, i18ndict

    def xmlnsattrs(self):
        newlist = []
        for prefix, uri in self.nsNew:
            if prefix:
                key = "xmlns:" + prefix
            else:
                key = "xmlns"
            if uri in (ZOPE_METAL_NS, ZOPE_TAL_NS, ZOPE_I18N_NS):
                item = (key, uri, "xmlns")
            else:
                item = (key, uri)
            newlist.append(item)
        self.nsNew = []
        return newlist

    def fixname(self, name):
        if ' ' in name:
            uri, name = name.split(' ')
            prefix = self.nsDict[uri]
            prefixed = name
            if prefix:
                prefixed = "%s:%s" % (prefix, name)
            ns = 'x'
            if uri == ZOPE_TAL_NS:
                ns = 'tal'
            elif uri == ZOPE_METAL_NS:
                ns = 'metal'
            elif uri == ZOPE_I18N_NS:
                ns = 'i18n'
            return (prefixed, name, ns)
        return (name, name, None)

    def EndElementHandler(self, name):
        name = self.fixname(name)[0]
        self.gen.emitEndElement(name)

    def DefaultHandler(self, text):
        self.gen.emitRawText(text)

"""Translation context object for the TALInterpreter's I18N support.

The translation context provides a container for the information
needed to perform translation of a marked string from a page template.

"""

DEFAULT_DOMAIN = "default"

class TranslationContext:
    """Information about the I18N settings of a TAL processor."""

    def __init__(self, parent=None, domain=None, target=None, source=None):
        if parent:
            if not domain:
                domain = parent.domain
            if not target:
                target = parent.target
            if not source:
                source = parent.source
        elif domain is None:
            domain = DEFAULT_DOMAIN

        self.parent = parent
        self.domain = domain
        self.target = target
        self.source = source

"""
Dummy TALES engine so that I can test out the TAL implementation.
"""

import re
import sys
import stat
import os
import traceback

class _Default:
    pass
Default = _Default()

name_match = re.compile(r"(?s)(%s):(.*)\Z" % NAME_RE).match

class CompilerError(Exception):
    pass

class AthanaTALEngine:

    position = None
    source_file = None

    __implements__ = ITALESCompiler, ITALESEngine

    def __init__(self, macros=None, context=None, webcontext=None, language=None, request=None):
        if macros is None:
            macros = {}
        self.macros = macros
        dict = {'nothing': None, 'default': Default}
        if context is not None:
            dict.update(context)

        self.locals = self.globals = dict
        self.stack = [dict]
        self.webcontext = webcontext
        self.language = language
        self.request = request

    def compilefile(self, file, mode=None):
        assert mode in ("html", "xml", None)
#         file =  join_paths(GLOBAL_ROOT_DIR,join_paths(self.webcontext.root, file))
        if mode is None:
            ext = os.path.splitext(file)[1]
            if ext.lower() in (".html", ".htm"):
                mode = "html"
            else:
                mode = "xml"
        if mode == "html":
            p = HTMLTALParser(TALGenerator(self))
        else:
            p = TALParser(TALGenerator(self))
        p.parseFile(file)
        return p.getCode()

    def getCompilerError(self):
        return CompilerError

    def getCompiler(self):
        return self

    def setSourceFile(self, source_file):
        self.source_file = source_file

    def setPosition(self, position):
        self.position = position

    def compile(self, expr):
        return "$%s$" % expr

    def uncompile(self, expression):
        assert expression.startswith("$") and expression.endswith("$"), expression
        return expression[1:-1]

    def beginScope(self):
        self.stack.append(self.locals)

    def endScope(self):
        assert len(self.stack) > 1, "more endScope() than beginScope() calls"
        self.locals = self.stack.pop()

    def setLocal(self, name, value):
        if self.locals is self.stack[-1]:
            self.locals = self.locals.copy()
        self.locals[name] = value

    def setGlobal(self, name, value):
        self.globals[name] = value

    def evaluate(self, expression):
        assert expression.startswith("$") and expression.endswith("$"), expression
        expression = expression[1:-1]
        m = name_match(expression)
        if m:
            type, expr = m.group(1, 2)
        else:
            type = "path"
            expr = expression
        if type in ("string", "str"):
            return expr
        if type in ("path", "var", "global", "local"):
            return self.evaluatePathOrVar(expr)
        if type == "not":
            return not self.evaluate("$" + expr + "$")
        if type == "exists":
            return self.locals.has_key(expr) or self.globals.has_key(expr)
        if type == "request":
            try:
                return eval(expr, {}, self.request.params)
            except NameError:
                return None
            except Exception as e:
                logg.error("error!", exc_info=1)
                raise TALESError("evaluation error in %s" % `expr`)
        if type == "python":
            try:
                return eval(expr, self.globals, self.locals)
            except Exception as e:
                logg.exception("exception in TAL python evaluation:")
                logg.error("trace for exception:")
                raise TALESError("evaluation error in %s" % `expr`, self.position)

        if type == "position":
            if self.position:
                lineno, offset = self.position
            else:
                lineno, offset = None, None
            return '%s (%s,%s)' % (self.source_file, lineno, offset)
        raise TALESError("unrecognized expression: " + `expression`)

    def evaluatePathOrVar(self, expr):
        expr = expr.strip()
        _expr=expr
        _f=None
        if expr.rfind("/")>0:
            pos=expr.rfind("/")
            _expr = expr[0:pos]
            _f = expr[pos+1:]
        if _expr in self.locals:
            if _f:
                return getattr(self.locals[_expr],_f)
            else:
                return self.locals[_expr]
        elif self.globals.has_key(_expr):
            if _f:
                return getattr(self.globals[_expr], _f)
            else:
                return self.globals[_expr]
        else:
            raise TALESError("unknown variable: %s" % `_expr`)

    def evaluateValue(self, expr):
        return self.evaluate(expr)

    def evaluateBoolean(self, expr):
        return self.evaluate(expr)

    def evaluateText(self, expr):
        text = self.evaluate(expr)
        if text is not None and text is not Default:
            if isinstance(text, str):
                return text.decode("utf8")
            else:
                return unicode(text)

    def evaluateStructure(self, expr):
        return self.evaluate(expr)

    def evaluateSequence(self, expr):
        return self.evaluate(expr)

    def evaluateMacro(self, macroName):
        assert macroName.startswith("$") and macroName.endswith("$"), macroName
        macroName = macroName[1:-1]
        file, localName = self.findMacroFile(macroName)
        if not file:
            macro = self.macros[localName]
        else:
            program, macros = self.compilefile(file)
            macro = macros.get(localName)
            if not macro:
                raise TALESError("macro %s not found in file %s" %
                                 (localName, file))
        return macro

    def findMacroDocument(self, macroName):
        # unused method and parsefile doesn't exist!
        raise NotImplementedError()
#         file, localName = self.findMacroFile(macroName)
#         if not file:
#             return file, localName
#         doc = parsefile(file)
#         return doc, localName

    def findMacroFile(self, macroName):
        if not macroName:
            raise TALESError("empty macro name")
        i = macroName.rfind('/')
        if i < 0:
            return None, macroName
        else:
            fileName = getMacroFile(macroName[:i])
            localName = macroName[i+1:]
            return fileName, localName

    def setRepeat(self, name, expr):
        seq = self.evaluateSequence(expr)
        self.locals[name] = Iterator(name, seq, self)
        return self.locals[name]

    def createErrorInfo(self, err, position):
        return ErrorInfo(err, position)

    def getDefault(self):
        return Default

    def translate(self, domain, msgid, mapping, default=None):
        global translators
        text = default or msgid
        for f in translators:
            text = f(msgid, language=self.language, request=self.request)
            try:
                text = f(msgid, language=self.language, request=self.request)
                if text and text!=msgid:
                    break
            except:
                pass
        def repl(m, mapping=mapping):
            return mapping[m.group(m.lastindex).lower()]
        return VARIABLE.sub(repl, text)


class Iterator:

    def __init__(self, name, seq, engine):
        self.name = name
        self.seq = iter(seq)
        self.engine = engine
        self.nextIndex = 0

    def next(self):
        self.index = i = self.nextIndex
        try:
            item = next(self.seq)
        except StopIteration:
            return 0
        self.nextIndex += 1
        self.engine.setLocal(self.name, item)
        return 1

    def even(self):
        logg.debug("-even-")
        return not self.index % 2

    def odd(self):
        logg.debug("-odd-")
        return self.index % 2

    def number(self):
        return self.nextIndex

    def parity(self):
        if self.index % 2:
            return 'odd'
        return 'even'

    def first(self, name=None):
        if self.start: return 1
        return not self.same_part(name, self._last, self.item)

    def last(self, name=None):
        if self.end: return 1
        return not self.same_part(name, self.item, self._next)

    def length(self):
        return len(self.seq)


VARIABLE = re.compile(r'\$(?:(%s)|\{(%s)\})' % (NAME_RE, NAME_RE))

parsed_files = {}
parsed_strings = {}

template_globals = {}

def runTAL(writer, context=None, string=None, file=None, macro=None, language=None, request=None, mode=None):

    if file:
        file = getMacroFile(file)

    if context is None:
        context = {}

    if string and not file:
        if string in parsed_strings:
            program,macros = parsed_strings[string]
        else:
            program,macros = None,None
    elif file and not string:
        if file in parsed_files:
            (program,macros,mtime) = parsed_files[file]
            mtime_file = os.stat(file)[stat.ST_MTIME]
            if mtime != mtime_file:
                program,macros = None,None
                mtime = mtime_file
        else:
            program,macros,mtime = None,None,None

    if not (program and macros):
        if file and file.endswith("xml") or mode=="xml":
            talparser = TALParser(TALGenerator(AthanaTALEngine()))
        else:
            talparser = HTMLTALParser(TALGenerator(AthanaTALEngine()))
        if string:
            talparser.parseString(string)
            (program, macros) = talparser.getCode()
            parsed_strings[string] = (program,macros)
        else:
            talparser.parseFile(file)
            (program, macros) = talparser.getCode()
            parsed_files[file] = (program,macros,mtime)

    if macro and macro in macros:
        program = macros[macro]
    engine = AthanaTALEngine(macros, context, language=language, request=request)
    TALInterpreter(program, macros, engine, writer, wrap=0)()

def str_processTAL(context=None, string=None, file=None, macro=None, language=None, request=None, mode=None):
    class STRWriter:
        def __init__(self):
            self.string = ""
        def write(self,text):
            if type(text) == type(u''):
                self.string += text.encode("utf-8")
            else:
                self.string += text
        def getvalue(self):
            return self.string
    wr = STRWriter()
    runTAL(wr, context, string=string, file=file, macro=macro, language=language, request=request, mode=mode)
    return wr.getvalue()

def processTAL(context=None, string=None, file=None, macro=None, language=None, request=None, mode=None):
    class UnicodeWriter:
        def __init__(self):
            self.string = u""
        def write(self,text):
            if isinstance(text, str):
                text = text.decode("utf8")
            self.string += text
        def getvalue(self):
            return self.string

    wr = UnicodeWriter()
    context.update(template_globals)
    runTAL(wr, context, string=string, file=file, macro=macro, language=language, request=request, mode=mode)
    return wr.getvalue()


class MyWriter:
    def write(self,s):
        sys.stdout.write(s)

def test():
    p = TALParser(TALGenerator(AthanaTALEngine()))
    file = "test.xml"
    if sys.argv[1:]:
        file = sys.argv[1]
    p.parseFile(file)
    program, macros = p.getCode()

    class Node:
        def getText(self):
            return "TEST"

    engine = AthanaTALEngine(macros, {'node': Node()})
    TALInterpreter(program, macros, engine, MyWriter(), wrap=0)()


def ustr(v):
    """Convert any object to a plain string or unicode string,
    minimising the chance of raising a UnicodeError. This
    even works with uncooperative objects like Exceptions
    """
    try:
        if type(v) == type(""): #isinstance(v, basestring):
            return v
        else:
            fn = getattr(v,'__str__',None)
            if fn is not None:
                v = fn()
                if isinstance(v, basestring):
                    return v
                else:
                    raise ValueError('__str__ returned wrong type')
            return str(v)
    except:
        try:
            return v.encode("utf-8")
        except:
            try:
                return unicode(v, 'utf-8').encode("utf-8")
            except:
                try:
                    return v.decode('latin1').encode('utf-8')
                except:
                    return v


##### additional stuff from athana that is needed for the TAL parser ###

#l 5923
def qualify_path(p):
    if p[-1] != '/':
        return p + "/"
    return p


def join_paths(p1,p2):
    if p1.endswith("/"):
        if p2.startswith("/"):
            return p1[:-1] + p2
        else:
            return p1 + p2
    else:
        if p2.startswith("/"):
            return p1 + p2
        else:
            return p1 + "/" + p2

#l 5940
translators = []
macroresolvers = []


#l 5945
def getMacroFile(filename):
    global macrofile_callback
    for r in macroresolvers:
        try:
            f = r(filename)
            if f is not None and os.path.isfile(f):
                return f
        except:
            pass
    if os.path.isfile(filename):
        return filename
    filename2 =  join_paths(GLOBAL_ROOT_DIR,filename)
    if os.path.isfile(filename2):
        return filename2
    raise IOError("No such file: "+filename2)

#l 6823
def setBase(base):
    global GLOBAL_ROOT_DIR
    GLOBAL_ROOT_DIR = qualify_path(base)


#l 6831
def addMacroResolver(m):
    global macroresolvers
    macroresolvers += [m]

def addTranslator(m):
    global translators
    translators += [m]

