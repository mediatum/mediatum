# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2016 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from __future__ import absolute_import
import os
import tempfile
from utils.fileutils import importFile, _find_unique_destname, getImportDir, importFileIntoDir,\
    importFileRandom

REALNAME_ROOT = "test"
SUFFIX = ".jpg"
REALNAME = REALNAME_ROOT + SUFFIX
CONTENT = "content"


def assert_imported_file_ok_and_unlink(file_obj, filetype="image", mimetype="image/jpeg", content=None):
    assert file_obj.exists
    assert file_obj.mimetype == mimetype
    assert file_obj.filetype == filetype

    if content:
        with file_obj.open() as f:
            assert f.read() == content

    file_obj.unlink()


def test_find_unique_destname_not_conflict():
    assert _find_unique_destname("test.jpg", "prefix") == os.path.join(getImportDir(), "prefixtest.jpg")


def test_find_unique_destname_conflict():
    import_dir = getImportDir()
    realname = "test.jpg"
    prefix = "my"
    path = os.path.join(import_dir, prefix + realname)

    with open(path, "w") as wf:
        wf.write("w")

    # _find_unique_destname should notice that the path already exists and count up to 1
    alternative_path = path.replace(prefix, prefix + "1_")
    assert _find_unique_destname(realname, prefix) == alternative_path
    os.unlink(path)


def _test_import_function_with_tempfile(import_func, *args):
    with tempfile.NamedTemporaryFile(suffix=SUFFIX) as f:
        f.write(CONTENT)
        f.flush()
        imported_file = import_func(*args, tempname=f.name)
        assert_imported_file_ok_and_unlink(imported_file, content=CONTENT)

    return imported_file


def test_importFile():
    _test_import_function_with_tempfile(importFile, REALNAME)



def test_importFileToRealname():
    imported_file = _test_import_function_with_tempfile(importFile, REALNAME)
    assert imported_file.base_name == REALNAME


def test_importFileIntoDir():
    _test_import_function_with_tempfile(importFileIntoDir, "testdir")


def test_importFileRandom():
    _test_import_function_with_tempfile(importFileRandom)
