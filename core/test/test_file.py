# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
import os

from pytest import raises, fixture

### setup
from core.test.setup import setup_with_db
setup_with_db()

from core.file import File, DATADIR
from core.test.asserts import assert_deprecation_warning
from core.test.fixtures import session_empty, some_file, some_file_real, some_file_in_subdir


@fixture(params=[
    File.getType,
    File.getMimeType,
    File.getName,
    File.retrieveFile,
    File.getSize])
def legacy_getter(request):
    return request.param


def test_init_deprecation_datadir(session_empty):
    path = os.path.join(DATADIR, "testfilename")
    assert_deprecation_warning(File, path, "ni", "spam")


def test_init_exception_old_keyword_args(session_empty):
    with raises(TypeError):
        File(name="ff", type="t", mimetype="x")


def test_legacy_getter_deprecation(some_file, legacy_getter):
    assert_deprecation_warning(legacy_getter, some_file)


def test_size(some_file_real):
    assert some_file_real.size == 4


def test_base_name(some_file_in_subdir):
    assert some_file_in_subdir.base_name == "filename"
