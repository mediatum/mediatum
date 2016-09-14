"""
 mediatum - a multimedia content repository

 Copyright (C) 2012 Arne Seifert <arne.seifert@tum.de>

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

import logging
import os
import re
import zipfile
import core.athana as athana
import core.config as config
import core.translation as translation

from core import webconfig
from core.users import getUserFromRequest
from core.transition import httpstatus

try:
    from reportlab.platypus import Paragraph, BaseDocTemplate, SimpleDocTemplate, FrameBreak, Frame, PageTemplate
    from reportlab.lib.units import cm
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.rl_config import defaultPageSize
    reportlab = 1
except:
    reportlab = 0


logg = logging.getLogger(__name__)

helppaths = ['web/help/']
items = {}
index = {}
paths = {}
all_paths = {}
map = {}
menustructure = []


def getHelpPath(path):
    if ".".join(filter(None, path)) in all_paths:
        return '/help/' + '/'.join(filter(None, path))
    else:
        return ''


def addHelpPath(path):
    if path not in helppaths:
        helppaths.append(path)
        initHelp()


def initHelp():
    logg.debug("..init help")

    def addHelpItem(i, part, dict):
        for j in range(i):
            dict = dict[part[j]]
        if part[i] not in dict:
            dict[part[i]] = {'lang': part[0]}

    if athana.GLOBAL_ROOT_DIR == "no-root-dir-set":
        athana.setBase(".")

    for helppath in helppaths:
        for root, dirs, filenames in os.walk(helppath):
            for filename in [f for f in filenames if f.endswith('zip')]:
                lang = filename.split(".")[0]
                parts = filename.split(".")
                if lang not in paths:
                    paths[lang] = []
                paths[lang].append(".".join(parts[1:-1]))
                if ".".join(parts[1:-1]) not in all_paths:
                    all_paths[".".join(parts[1:-1])] = []
                if parts[0] not in all_paths[".".join(parts[1:-1])]:
                    all_paths[".".join(parts[1:-1])].append(parts[0])

                if ".".join(parts[1:-1]) not in map:
                    map[".".join(parts[1:-1])] = {}
                if parts[0] not in map[".".join(parts[1:-1])]:
                    map[".".join(parts[1:-1])][parts[0]] = []

                c = None
                for con in athana.contexts:
                    if con.name == "/help/%s/" + "/".join(parts[:-1]) + "/":
                        c = con
                        break
                if not c:
                    c = athana.addFileStore("/help/" + "/".join(parts[:-1]) + "/", helppath + filename)

                # translations
                try:
                    if c.handlers[0].filesystem.isfile('translation.po'):
                        fi = c.handlers[0].filesystem.open('translation.po', 'rb')
                        id = None
                        for line in fi.read().split("\n"):
                            if line.startswith("msgid") or "msgid " in line:
                                id = re.sub(r'^\"|\"$', '', " ".join(line.split(" ")[1:]).strip())
                            elif line.startswith("msgstr"):
                                map[".".join(parts[1:-1])][parts[0]].append((id, re.sub(r'^\"|\"$', '', line[6:].strip())))
                        fi.close()
                        translation.addLabels(map[".".join(parts[1:-1])])
                except:
                    pass

                # index values
                if lang not in index.keys():
                    index[lang] = {}
                if c.handlers[0].filesystem.isfile('index.txt'):
                    fi = c.handlers[0].filesystem.open('index.txt', 'rb')
                    for line in re.sub(r'\r', '', fi.read()).strip().split("\n"):
                        if line not in index[lang]:
                            index[lang][line] = []
                        if filename.replace("index.txt", "") not in index[lang][line]:
                            index[lang][line].append(filename.replace("index.txt", ""))

                # help items
                for i in range(len(parts) - 1):
                    try:
                        addHelpItem(i, parts, items)
                    except:
                        pass

initHelp()


def addExtItem(curlang, path, items):
    p = path.split(".")
    if p[0] != "":
        it = items
        for i in range(len(p) - 1):
            if p[i] not in it:
                it[p[i]] = {'lang': curlang}
            it = it[p[i]]

        if not p[-1] in it.keys():
            it[p[-1]] = {'lang': all_paths[path][0]}
        translation.addLabels({curlang: map[path][all_paths[path][0]]})  # add translations for module


def getHelp(req):
    global menustructure, items, paths, all_paths, index

    v = {'user': getUserFromRequest(req)}

    if "language_change" in req.params:  # change language
        req.session["language"] = req.params.get('language_change')
    language = translation.lang(req)

    if "edit.x" in req.params:  # edit content
        logg.debug("edit page")

    if "refresh.x" in req.params:  # refresh content
        menustructure = []
        index = {}
        items = {}
        paths = {}
        all_paths = {}
        initHelp()

    if req.path[-1] == "/":
        req.path = req.path[:-1]

    if re.sub('^\.', '', req.path.replace("/", ".")) in all_paths:
        pathlangs = all_paths[re.sub('^\.', '', req.path.replace("/", "."))]
        if language not in pathlangs:
            content = getHelpFileContent(req.path, pathlangs[0])
        else:
            content = getHelpFileContent(req.path, language)
    else:  # page not found 404
        req.setStatus(httpstatus.HTTP_NOT_FOUND)
        content = req.getTAL(webconfig.theme.getTemplate("help.html"), {}, macro='notfound')

    if "export" in req.params:
        if req.params.get('export') == "pdf":
            logg.debug("deliver pdf")
            req.reply_headers['Content-Type'] = "application/pdf; charset=utf-8"
            content = content.replace('"/help/', '"http://' + config.get('host.name') + '/help/')
            req.write(buildHelpPDF(req.params.get('url'), language))
            return
    if language not in menustructure:
        menustructure.append(language)
        for path in all_paths:
            addExtItem(language, path, items[language])

    v['content'] = content
    v['languages'] = config.languages
    v['curlang'] = translation.lang(req)
    v['items'] = items[translation.lang(req)]
    v['path'] = req.path.split("/")[1:]
    v['url'] = req.path
    v['indexvalues'] = index[language]
    indexchars = sorted(set([i[0].upper() for i in index[language].keys()]))
    v['indexchars'] = indexchars
    req.writeTAL(webconfig.theme.getTemplate("help.html"), v, macro='help')


def getHelpFileContent(path, language, z_file='web/help/%s%s.zip'):
    content = ""
    z_file = z_file % (language, path.replace("/", "."))
    try:
        zf = zipfile.ZipFile(z_file)
        content = zf.read('index.html')
        content = content.replace('src="./', 'src="/help/' + language + path + '/')
    except:
        for helppath in helppaths:
            if os.path.exists(helppath + '/%s%s.zip' % (language, path.replace("/", "."))):
                return getHelpFileContent(path, language, z_file=helppath + '/%s%s.zip')
    return content


class HelpPdf:

    def __init__(self, path, language, content=""):
        self.styleSheet = getSampleStyleSheet()
        self.path = path
        self.language = language
        self._pages = 1
        self.data = []
        self.content = content

    def myPages(self, canvas, doc):
        doc.pageTemplate.frames = self.getStyle(self._pages)
        canvas.saveState()
        canvas.setFont('Helvetica', 8)
        canvas.restoreState()
        self._pages += 1

    def getStyle(self, page):
        frames = []

        if page == 1:  # first page
            # main header
            frames.append(Frame(1 * cm, 25.5 * cm, 19 * cm, 3 * cm, leftPadding=0, rightPadding=0, id='normal', showBoundary=0))
            frames.append(Frame(1 * cm, 2 * cm, 19 * cm, 23 * cm, leftPadding=0, rightPadding=0, id='normal', showBoundary=0))  # content
        else:
            # content page>1
            frames.append(Frame(1 * cm, 2 * cm, 19 * cm, 26.5 * cm, leftPadding=0, rightPadding=0, id='normal', showBoundary=0))
        return frames

    def build(self, style=1):
        self.h1 = self.styleSheet['Heading1']
        self.h1.fontName = 'Helvetica'
        self.bv = self.styleSheet['BodyText']
        self.bv.fontName = 'Helvetica'
        self.bv.fontSize = 7
        self.bv.spaceBefore = 0
        self.bv.spaceAfter = 0

        self.header = self.styleSheet['Heading3']
        self.header.fontName = 'Helvetica'

        self.data.append(Paragraph(translation.t(self.language, 'mediatumhelptitle'), self.h1))
        self.data.append(Paragraph(self.path, self.bv))

        self.data.append((FrameBreak()))

        # format content
        self.content = self.content.replace("\n", "")
        repl = {'p': 'BodyText', 'h1': 'Heading1', 'h2': 'Heading2', 'h3': 'Heading3', 'h4': 'Heading4', 'h5': 'Heading5', 'li': 'Bullet'}
        curstyle = "BodyText"
        for item in re.split(r'<(p|h[1-5]|li)>|<(/p|/h[1-5]|/li)>', self.content):
            if item and item != "":
                if item in repl.keys():
                    curstyle = repl[item]
                elif item[0] == "/" and item[1:] in repl.keys():
                    curstyle = ""
                else:
                    if item.strip != "" and curstyle != "":
                        logg.debug('add %s --> %s')
                        if curstyle == "Bullet":
                            item = "- " + item
                            logg.debug("bullet %s", item)
                        self.data.append(Paragraph(item, self.styleSheet[curstyle]))

        template = SimpleDocTemplate(config.get("paths.tempdir", "") + "help.pdf", showBoundary=0)
        tFirst = PageTemplate(id='First', onPage=self.myPages, pagesize=defaultPageSize)
        tNext = PageTemplate(id='Later', onPage=self.myPages, pagesize=defaultPageSize)

        template.addPageTemplates([tFirst, tNext])
        template.allowSplitting = 1
        BaseDocTemplate.build(template, self.data)

        template.canv.setAuthor(translation.t(self.language, "main_title"))
        template.canv.setTitle("%s \n'%s' - %s: %s" % (translation.t(self.language, "edit_stats_header"),
                                                       'sdfsdfsdf', translation.t(self.language, "edit_stats_period_header"), '2003'))
        return template.canv._doc.GetPDFData(template.canv)


def buildHelpPDF(path, language):
    if not reportlab:
        return None
    p = path.replace("http://" + config.get('host.name') + '/help', '')
    content = getHelpFileContent(p, language)
    content = content.replace('"/help/', '"http://' + config.get('host.name') + '/help/')

    _pdf = HelpPdf(path, language, content=content)
    return _pdf.build()
