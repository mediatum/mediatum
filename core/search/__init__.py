from .language import parser

class SearchQueryException(ValueError):
    pass

def parse_searchquery(searchquery):
    try:
        searchtree = parser.parse_string(searchquery)
    except Exception:
        raise SearchQueryException("search query cannot be parsed: " + searchquery)

    return searchtree