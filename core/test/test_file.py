# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
import os

from pytest import raises, fixture

from core import File
from core import config
from core.test.asserts import assert_deprecation_warning


@fixture(params=[
    File.getType,
    File.getMimeType,
    File.getName,
    File.retrieveFile,
    File.getSize])
def legacy_getter(request):
    return request.param


def test_init_deprecation_datadir():
    path = os.path.join(config.settings["paths.datadir"], "testfilename")
    assert_deprecation_warning(File, path, "ni", "spam")


def test_init_exception_old_keyword_args():
    with raises(TypeError):
        File(name="ff", type="t", mimetype="x")


def test_legacy_getter_deprecation(some_file, legacy_getter):
    assert_deprecation_warning(legacy_getter, some_file)


def test_size(some_file_real):
    assert some_file_real.size == 4


def test_base_name(some_file_in_subdir):
    assert some_file_in_subdir.base_name == "filename"


def test_unlink_after_deletion(session, some_file_real):
    session.commit()
    assert some_file_real.exists
    some_file_real.unlink_after_deletion = True
    session.delete(some_file_real)
    session.commit()
    # unlink_after_deletion is set, file should be gone now
    assert not some_file_real.exists


def test_unlink_after_deletion_default_disabled(session, some_file_real):
    session.commit()
    assert some_file_real.exists
    session.delete(some_file_real)
    session.commit()
    # files should not be unlinked by default on object deletion by default, so it must still be there
    assert some_file_real.exists


def test_get_sha512(session, some_file_real):
    session.commit()
    assert some_file_real.exists
    #session.delete(some_file_real)
    sha, created = some_file_real.get_or_create_sha512()
    assert created == True
    assert sha
    assert len(sha) == 128
    # test correct calculatation of the sha512 of an empty file
    with open(some_file_real.abspath, 'w') as f:
        f.truncate()
    sha = some_file_real.update_sha512()
    assert sha.startswith('cf83e1357eefb8bdf1542850d6')


def test_verify_checksum(session, some_file_real):
    session.commit()
    sha, created = some_file_real.get_or_create_sha512()
    assert created
    assert some_file_real.verify_checksum() is True
    # test detection of changes in content
    with open(some_file_real.abspath, 'w') as f:
        f.write('file content has changed')
    assert some_file_real.verify_checksum() is False
    # test handling of deleted file
    os.unlink(some_file_real.abspath)
    assert some_file_real.verify_checksum() is None


def test_get_sha_no_file(session, some_file):
    session.commit()
    sha, new = some_file.get_or_create_sha512()
    assert sha is None

def test_check_sha_no_file(session, some_file):
    session.commit()
    file_ok = some_file.verify_checksum()
    assert file_ok is None
