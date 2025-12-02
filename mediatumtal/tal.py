# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import print_function
from __future__ import division, absolute_import

from mediatumtal import talextracted
from mediatumtal.talextracted import processTAL, str_processTAL
from mediatumtal.talextracted import runTAL  # @UnusedImport


def str_getTAL(page, context, macro=None, language=None, request=None):
    return str_processTAL(context, file=page, macro=macro, language=language, request=request)

def getTAL(page, context, macro=None, language=None, request=None):
    return processTAL(context, file=page, macro=macro, language=language, request=request)

def getTALstr(string, context, macro=None, language=None, mode=None):
    # processTAL doesn't support unicode template strings, let's encode it first
    if isinstance(string, unicode):
        string = string.encode("utf8")
    return processTAL(context, string=string, macro=macro, language=language, mode=mode)


def set_base(basedir):
    talextracted.setBase(basedir)


def add_translator(translator):
    talextracted.addTranslator(translator)


def add_macro_resolver(macroresolver):
    talextracted.addMacroResolver(macroresolver)


def add_template_globals(**kwargs):
    """Adds globals from a dict which will be available in all template contexts"""
    talextracted.template_globals.update(kwargs)
