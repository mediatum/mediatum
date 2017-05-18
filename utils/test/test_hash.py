# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2016 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from __future__ import absolute_import
import tempfile

from utils.utils import sha512_from_file


def test_sha512_nonexisting_file():
    sha = sha512_from_file('')
    assert sha is None


def test_sha512_empty_file():
    # full sha512 of an empty file is
    # cf83e1357eefb8bdf1542850d66d8007d620e4050b5715dc83f4a921d36ce9ce47d0d13c5d85f2b0ff8318d2877eec2f63b931bd47417a81a538327af927da3e
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.close()
    sha = sha512_from_file(f.name)
    assert sha.startswith('cf83e1357eefb8bdf1542850d66d8007d620e4050b5715dc83f4a921d36ce9ce47d0d13c5d85f2b0ff8318d2877')


def test_sha512_file_with_content():
    # full sha512 is
    # 8ab47d6852cccaadc621dc9cdb6d2ab17c7fb905d261ba59067763e78ec542f0eb75a30caf4df3a10c4dc25911107d6e4e21bc5c79226182f5c031548451e1da
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write('mediatum_test\n')
    sha = sha512_from_file(f.name)
    assert sha.startswith('8ab47d6852cccaadc621dc9cdb6d2ab17c7fb905d261ba59067763e78ec542f0eb75a30caf4df3a10c4dc259111')
