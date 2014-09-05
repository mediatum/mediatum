# -*- coding: utf-8 -*-

from __future__ import division, absolute_import, print_function

import importlib
from jinja2 import Markup

class CSSIncludes(object):
    def __init__(self, debug=True):
        includes = "utils.css_includes_debug" if debug else "utils.css_includes"
        self.includes = importlib.import_module(includes)


class JavascriptIncludes(object):
    def __init__(self, debug=True):
        includes = "utils.js_includes_debug" if debug else "utils.js_includes"
        self.includes = importlib.import_module(includes)

    def include_jquery(self, version="2.0.3", location="/js"):
        return Markup(self.includes.jquery.format(version=version, location=location))

    def include_datatables(self, version="1.9.4", location="/js"):
        return Markup(self.includes.datatables.format(version=version, location=location))

    def include_bootstrap(self, version="3.1.1", location="/js"):
        return Markup(self.includes.bootstrap.format(version=version, location=location))
