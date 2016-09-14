# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2016 by the mediaTUM authors
    :license: GPL3, see COPYING for details

    Some tests in this package need physical test files that are not included in the mediaTUM distribution.
    Please provide them in the locations specified below or some test will be skipped automatically.
"""
import os
import pytest
from pytest import fixture
from core import File
from core.config import resolve_datadir_path
from contenttypes.test.factories import VideoFactory
from schema.test.factories import MetadatatypeFactory


# must be relative to datadir

# mime subtype -> path relative to datadir
TEST_IMAGE_PATHS = {
    "tiff": "test/tiff.tif",
    "jpeg": "test/jpeg.jpg",
    "png": "test/png.png",
    "svg+xml": "test/svg+xml.svg",
    "gif": "test/gif.gif",
}


def fullpath_to_test_image(mimetype):
    relpath = TEST_IMAGE_PATHS[mimetype]
    return resolve_datadir_path(relpath)


# must be relative to datadir
TEST_VIDEO_NAME = u"test_video.mp4"
TEST_VIDEO_PATH = u"test/" + TEST_VIDEO_NAME

test_video_fullpath = resolve_datadir_path(TEST_VIDEO_PATH)

skip_if_video_missing = pytest.mark.skipif(not os.path.exists(test_video_fullpath),
                                           reason=u"test video not found at " + test_video_fullpath)
