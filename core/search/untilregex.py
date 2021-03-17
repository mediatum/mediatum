# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from __future__ import division
from __future__ import print_function

import re
import parcon


class UntilRegex(parcon._RParser):
    """
    """

    def __init__(self, regex, flags=re.UNICODE):
        self.regex = re.compile(regex, flags)

    def parse(self, text, position, end, space):
        position = start = space.consume(text, position, end)
        regex_match = self.regex.search(text, position, end)
        if regex_match:
            position = regex_match.start()
            return parcon.match(position, text[start:position].strip(), [(position, parcon.EUnsatisfiable())])
        else:
            return parcon.failure("regex not found")

    def create_railroad(self, options):
        return parcon._rr.Token(parcon._rr.PRODUCTION, "UntilRegex(" + self.regex.pattern + ")")

    def __repr__(self):
        return "UntilRegex(%s)" % repr(self.parser)
