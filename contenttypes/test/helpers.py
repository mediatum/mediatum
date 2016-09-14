# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2016 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from __future__ import absolute_import
from contextlib import contextmanager


@contextmanager
def call_event_files_changed(node):
    node_filepaths_before = set(f.path for f in node.files)
    try:
        node.event_files_changed()
        yield
    finally:
        for generated_file in node.files:
            if generated_file.path not in node_filepaths_before:
                generated_file.unlink()
