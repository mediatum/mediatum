# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2016 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from __future__ import absolute_import
import os
import pytest

from core import config, File
from contenttypes.test import TEST_VIDEO_PATH, skip_if_video_missing, TEST_VIDEO_NAME


def assert_thumbnails_and_video_ok(video):
    files = video.files.order_by(File.filetype).all()
    assert files[0].filetype == u"presentation"
    assert files[0].mimetype == u"image/jpeg"
    assert files[0].path == TEST_VIDEO_PATH.replace(u".mp4", u".presentation")
    assert files[1].filetype == u"thumb"
    assert files[1].mimetype == u"image/jpeg"
    assert files[1].path == TEST_VIDEO_PATH.replace(u".mp4", u".thumb")
    assert files[2].filetype == u"video"
    assert files[2].mimetype == u"video/mp4"
    for f in files:
        assert os.path.isfile(f.abspath)
        assert os.stat(f.abspath).st_size > 0


def test_prepareData_data_access(session, video, req):
    session.flush()
    video.has_data_access = lambda *a, **k: True
    data = video._prepareData(req)
    assert data["video_url"] == u"/file/{}/{}".format(video.id, TEST_VIDEO_NAME)


def test_prepareData_no_data_access(video, req):
    video.has_data_access = lambda *a, **k: False
    data = video._prepareData(req)
    assert data["video_url"] is None


def test_show_node_big_video_url(video, req):
    video.has_data_access = lambda *a, **k: True
    html = video.show_node_big(req)
    assert u"/file/{}/{}".format(video.id, TEST_VIDEO_NAME) in html


@skip_if_video_missing
@pytest.mark.slow
def test_event_files_changed_new_video(video):
    video.system_attrs[u"thumbframe"] = None
    # event_files_changed should generate a small thumb and a larger thumb2, both jpegs
    video.event_files_changed()
    assert_thumbnails_and_video_ok(video)


@skip_if_video_missing
@pytest.mark.slow
def test_event_files_changed_new_video_thumbframe(video):
    # event_files_changed should generate a small thumb and a larger thumb2, both jpegs
    video.system_attrs[u"thumbframe"] = 5
    video.event_files_changed()
    assert_thumbnails_and_video_ok(video)
