# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""

from warnings import warn


class MInt(int):
    """'Magic' class which represents an integer value but converts itself to a string if needed.
    We need this because legacy code treats node ids as string and concatenates ids to strings.
    This is a stupid idea, so it raises a DeprecationWarning if it's used as a string ;)
    """

    def __new__(cls, value):
        return int.__new__(cls, value)

    def __add__(self, other):
        if isinstance(other, basestring):
            warn("magic cast int --> unicode in addition (left op)", DeprecationWarning)
            return unicode(self) + other
        return int.__add__(self, other)

    def __radd__(self, other):
        if isinstance(other, basestring):
            warn("magic cast int --> unicode in addition (right op)", DeprecationWarning)
            return other + unicode(self)
        return int.__add__(self, other)
    
    def __unicode__(self):
        return int.__str__(self)


