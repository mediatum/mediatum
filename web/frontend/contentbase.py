# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2016 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""


class ContentBase(object):
    """Abstract base class for everything that can be shown in the content area.
    """
    
    @property
    def node(self):
        raise NotImplementedError("must be implemented!")

    @property
    def logo(self):
        return

    @property
    def content_styles(self):
        return []

    def select_style_link(self, style):
        return ""
    
    def html(self, req):
        """Renders the component. Must return an unicode string (containing HTML)"""
        return u""

    def feedback(self, req):
        """Consumes request parameters and changes the internal state.
        No return value expected.
        """
        
    @property
    def cache_duration(self):
        """Returns the duration for which the content can be cached (HTTP proxies, for example)"""
        return 0