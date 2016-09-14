# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2016 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from __future__ import absolute_import
from core.archive import register_archive, archives, get_archive_for_node, Archive
from munch import Munch


def test_register_archive(fake_archive):
    archives.clear()
    register_archive(fake_archive)
    assert archives[fake_archive.archive_type] is fake_archive


def test_get_archive_for_node(fake_archive):
    node = Munch(system_attrs=Munch(archive_type=u"test"))
    archive = get_archive_for_node(node)
    assert archive is fake_archive


def test_fetch_file_from_archive(fake_archive):
    node = Munch(system_attrs=Munch(archive_path=u"testpath.jpg"))
    assert fake_archive.get_state(node) == Archive.NOT_PRESENT
    fake_archive.fetch_file_from_archive(node)
    assert fake_archive.get_state(node) == Archive.PRESENT
