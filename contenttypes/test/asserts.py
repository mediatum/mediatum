# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2016 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from __future__ import absolute_import
import os
from core import File
from utils.testing import make_files_munch


def assert_thumbnails_ok(node):
    files = make_files_munch(node)
    assert u"thumb" in files
    assert u"presentation" in files
    assert files.thumb.mimetype == u"image/jpeg"
    assert files.presentation.mimetype == u"image/jpeg"
    original_file = files[node.get_original_filetype()]
    base_filepath = os.path.splitext(original_file.path)[0]
    assert files.thumb.path == base_filepath + ".thumb"
    assert files.presentation.path == base_filepath + ".presentation"

    for f in [files.thumb, files.presentation]:
        assert os.path.isfile(f.abspath)
        assert os.stat(f.abspath).st_size > 0

