# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2016 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from __future__ import absolute_import

from contenttypes.video import Video
from contenttypes.image import Image
from core.test.factories import NodeFactory


class ImageFactory(NodeFactory):

    class Meta:
        model = Image

    schema = u"test"


class VideoFactory(NodeFactory):

    class Meta:
        model = Video

    schema = u"test"
