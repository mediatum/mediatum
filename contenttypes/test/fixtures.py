# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2016 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from __future__ import absolute_import
from pytest import fixture
from core import File
from contenttypes.test.factories import VideoFactory
from schema.test.factories import MetadatatypeFactory
from contenttypes.test import TEST_VIDEO_PATH


@fixture
def video(session):
    video = VideoFactory()
    MetadatatypeFactory(name=u"test")
    video.files.append(File(path=TEST_VIDEO_PATH, filetype=u"video", mimetype=u"video/mp4"))
    return video
