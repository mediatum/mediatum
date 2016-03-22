# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2016 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from __future__ import absolute_import

from contenttypes.video import Video
from core.test.factories import NodeFactory


class VideoFactory(NodeFactory):

    class Meta:
        model = Video

    schema = u"test"
