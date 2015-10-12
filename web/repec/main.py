"""
 mediatum - a multimedia content repository

 Copyright (C) 2007 Arne Seifert <seiferta@in.tum.de>
 Copyright (C) 2007 Matthias Kramm <kramm@in.tum.de>
 Copyright (C) 2015 Andreas Stocker <as@anexia.at>

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
import re

from web.repec.content import HTMLCollectionContent, CollectionArchiveContent, CollectionSeriesContent, \
    HTMLCollectionJournalContent, CollectionJournalContent, HTMLCollectionPaperContent, \
    CollectionPaperContent, HTMLCollectionBookContent, CollectionBookContent


def repec(req):
    patterns = {
        r"/repec/[\d\w]+/wpaper/$": _wpaper,
        r"/repec/[\d\w]+/wpaper/papers.rdf$": _wpaper_rdf,
        r"/repec/[\d\w]+/journl/$": _journl,
        r"/repec/[\d\w]+/journl/journals.rdf$": _journl_rdf,
        r"/repec/[\d\w]+/ecbook/$": _ecbook,
        r"/repec/[\d\w]+/ecbook/books.rdf$": _ecbook_rdf,
        r"/repec/[\d\w]+/[\d\w]+seri.rdf$": _collection_seri,
        r"/repec/[\d\w]+/[\d\w]+arch.rdf$": _collection_arch,
        r"/repec/[\d\w]+/$": _collection,
    }
    url = req.fullpath

    for pattern, handler in patterns.items():
        if re.match(pattern, url):
            return handler(req)

    return req.error(404, "Unknown RePEc URL")


def _collection(req):
    req['Content-Type'] = 'text/html; charset=utf-8'

    content = HTMLCollectionContent(req)
    return content.respond()


def _collection_arch(req):
    req['Content-Type'] = 'text/plain; charset=utf-8'

    content = CollectionArchiveContent(req)
    return content.respond()


def _collection_seri(req):
    req['Content-Type'] = 'text/plain; charset=utf-8'

    content = CollectionSeriesContent(req)
    return content.respond()


def _journl(req):
    req['Content-Type'] = 'text/html; charset=utf-8'

    content = HTMLCollectionJournalContent(req)
    return content.respond()


def _journl_rdf(req):
    req['Content-Type'] = 'text/plain; charset=utf-8'

    content = CollectionJournalContent(req)
    return content.respond()


def _wpaper(req):
    req['Content-Type'] = 'text/html; charset=utf-8'

    content = HTMLCollectionPaperContent(req)
    return content.respond()


def _wpaper_rdf(req):
    req['Content-Type'] = 'text/plain; charset=utf-8'

    content = CollectionPaperContent(req)
    return content.respond()


def _ecbook(req):
    req['Content-Type'] = 'text/html; charset=utf-8'

    content = HTMLCollectionBookContent(req)
    return content.respond()


def _ecbook_rdf(req):
    req['Content-Type'] = 'text/plain; charset=utf-8'

    content = CollectionBookContent(req)
    return content.respond()
