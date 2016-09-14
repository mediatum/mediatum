import logging
from .language import parser
from core.search.oldparser import FtsSearchParser
from core.search.oldtonewtree import old_searchtree_to_new

logg = logging.getLogger(__name__)


class SearchQueryException(ValueError):
    pass


def parse_searchquery(searchquery):
    try:
        searchtree = parser.parse_string(searchquery)
    except Exception:
        msg = "search query cannot be parsed: " + searchquery
        logg.exception(msg)
        raise SearchQueryException(msg)

    return searchtree


def parse_searchquery_old_style(searchquery):
    old_parser = FtsSearchParser()
    try:
        old_searchtree = old_parser.parse(searchquery)
    except Exception:
        # XXX: can this be more specific?
        msg = "search query cannot be parsed: " + searchquery
        logg.exception(msg)
        raise SearchQueryException(msg)

    new_searchtree = old_searchtree_to_new(old_searchtree)
    return new_searchtree
