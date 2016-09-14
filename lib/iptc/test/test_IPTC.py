#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
 mediatum - a multimedia content repository

 Copyright (C) 2007 Arne Seifert <seiferta@in.tum.de>
 Copyright (C) 2007 Matthias Kramm <kramm@in.tum.de>

 This program is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.

 This program is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
import os
import pytest
import random
import string
from lib.iptc.IPTC import get_iptc_tags, get_wanted_iptc_tags, write_iptc_tags
from lib.iptc import IPTC
from utils.date import parse_date


@pytest.fixture
def less_tags():
    return {
        'ApplicationRecordVersion': 'ApplicationRecordVersion |5',
        'Caption-Abstract': 'Caption-Abstract |2000',
        'By-line': 'By-line |32',
        'Keywords': 'Keywords |64',
        'City': 'City |32'
    }


@pytest.fixture
def small_iptc_return():
    return \
        {
            'ApplicationRecordVersion': "4",
            'Keywords': '1;2;3'
        }


@pytest.fixture
def standard_date():
    return '2015:12:30'


@pytest.fixture
def iso_date():
    return '2015-12-30T00:00:00'


@pytest.fixture
def read_dict():
    return {
        'ApplicationRecordVersion': 4,
        'Caption-Abstract': 'abstract'
    }


@pytest.fixture
def write_dict():
    return {
        'Caption-Abstract': 'abstract'
    }


# can't use fixures in mark.parametrized bug #349 py.test (github)
TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), 'test_data/')


def _test_data_filepath(filename):
    return os.path.join(TEST_DATA_DIR, filename)


EMPTY_IPTC_TIF = _test_data_filepath('empty.tif')
EMPTY_IPTC_JPG = _test_data_filepath('empty.jpg')

FULL_IPTC_TIF = _test_data_filepath('keywords_list.tif')
FULL_IPTC_JPG = _test_data_filepath('keywords_list.tif')

DATE_JPG = _test_data_filepath('date.jpg')
RANDOM_TIF = _test_data_filepath('random.tif')

WRITE_UNICODE_TIF = _test_data_filepath('write.tif')
WRITE_UNICODE_JPG = _test_data_filepath('write.jpg')


def rand_unicode():
    ''' generates some random
        unicode string (of course not all u ;)
    '''
    b = ['03', '30']  # ?
    l = ''.join([random.choice('ABCDEF0123456789') for x in xrange(2)])
    return unichr(random.choice((0x300, 0x2000)) + random.randint(0, 0xff))


def str_gen(size=6, chars='{}{}'.format(string.ascii_uppercase, string.digits)):
    ''' generates a random string
        with a desired lenth
        according to security (not needed)
        SystemRandom is not to be used
    '''
    return ''.join(random.choice(chars) for _ in range(size))


class TestGetWanted_testValues(object):
    ''' tests the exact value returned
        by lib.iptc.IPTC.get_wanted_tags
        and test iptc values read from file
    '''

    def test_get_wanted_iptc_tags(self):
        assert get_wanted_iptc_tags()

    def test_get_iptc_tags_tif(self, small_iptc_return):
        res = get_iptc_tags(FULL_IPTC_TIF)
        assert res == small_iptc_return

    def test_get_iptc_tags_jpg(self, small_iptc_return):
        res = get_iptc_tags(FULL_IPTC_JPG)
        assert res == small_iptc_return


class TestEmptyFilePathes(object):
    ''' tests for crash conditions
        for empty .tif and .jpg
    '''
    @pytest.mark.parametrize("file_path, expected",
                             [
                                 (None, None),
                                 ('', None),
                                 ('-', None),
                                 (EMPTY_IPTC_TIF, {})
                             ])
    def test_iptc_values_empty_tif(self, less_tags, file_path, expected):
        assert get_iptc_tags(file_path, less_tags) == expected

    @pytest.mark.parametrize("file_path, expected",
                             [
                                 (None, None),
                                 ('', None),
                                 ('-', None),
                                 (EMPTY_IPTC_JPG, {})
                             ])
    def test_iptc_values_empty_jpg(self, less_tags, file_path, expected):
        assert get_iptc_tags(file_path, less_tags) == expected


class TestEmptyIPTCValues(object):
    ''' tests for empty iptc
    '''

    def test_iptc_values_empty_tif(self, less_tags):
        assert get_iptc_tags(EMPTY_IPTC_TIF, less_tags) == {}

    def test_iptc_values_empty_jpg(self, less_tags):
        assert get_iptc_tags(EMPTY_IPTC_JPG, less_tags) == {}


# XXX: does not work
class DISABLED_TestIsoDate(object):

    def test_iso_date(self, iso_date):
        assert parse_date(get_iptc_tags(DATE_JPG, ['DateCreated']), format='%Y:%m:%d') == iso_date


# XXX: write tests disabled, writing will be implemented later in #782
class DISABLED_TestWriteIPTC(object):

    def test_write_jpg(self, less_tags, write_dict, read_dict, random_jpg):
        write_iptc_tags(random_jpg, write_dict)
        assert get_iptc_tags(random_jpg, less_tags) == read_dict

    def test_write_tif(self, less_tags, write_dict, read_dict, random_tif):
        write_iptc_tags(random_tif, write_dict)
        assert get_iptc_tags(random_tif, less_tags) == read_dict

    def test_write_acii(self, write_ascii_jpg, write_ascii_tif):
        rnd_ascii = str_gen(2000)

        tag_dict = {'Caption-Abstract': u'{}'.format(rnd_ascii)}
        write_iptc_tags(write_ascii_jpg, tag_dict)
        write_iptc_tags(write_ascii_tif, tag_dict)

        ret_dict_jpg = get_iptc_tags(write_ascii_jpg)
        ret_dict_tif = get_iptc_tags(write_ascii_tif)

        assert ret_dict_jpg['Caption-Abstract'] == rnd_ascii
        assert ret_dict_tif['Caption-Abstract'] == rnd_ascii

    def test_write_acii_tags(self, write_ascii_jpg, write_ascii_tif):
        tags = get_wanted_iptc_tags()

        for tag in tags:
            choice_tag = random.choice(tags.keys())
            if int(tags[choice_tag].split('|')[-1]) > 127:
                str_len = int(tags[choice_tag].split('|')[-1])
                break

        rnd_ascii = str_gen(str_len)

        tag_dict = {'{}'.format(choice_tag.split('iptc_')[-1]): u'{}'.format(rnd_ascii)}

        write_iptc_tags(write_ascii_jpg, tag_dict)
        write_iptc_tags(write_ascii_tif, tag_dict)

        ret_dict_jpg = get_iptc_tags(write_ascii_jpg)
        ret_dict_tif = get_iptc_tags(write_ascii_tif)

        assert ret_dict_jpg[choice_tag] == rnd_ascii
        assert ret_dict_tif[choice_tag] == rnd_ascii

    def test_write_unicode(self):
        ''' writes a single unicode char into a jpg and tif
            image and compares the read solutions by
            according to available unicode codepoints
            random sequenzes of generated unicode
            strings could not be checked
        '''
        rnd_unicode = rand_unicode()

        write_iptc_tags(WRITE_UNICODE_JPG, {'Caption-Abstract': u'{}'.format(rnd_unicode)})
        write_iptc_tags(WRITE_UNICODE_TIF, {'Caption-Abstract': u'{}'.format(rnd_unicode)})

        ret_dict = get_iptc_tags(WRITE_UNICODE_JPG)

        assert ret_dict['iptc_Caption-Abstract'].encode('utf-8') == rnd_unicode.encode('utf-8')
        assert ret_dict['iptc_Caption-Abstract'].encode('utf-8') == rnd_unicode.encode('utf-8')


class TestIPTCKeywords(object):

    def test_keywords_jpg(self, small_iptc_return):
        res = get_iptc_tags(FULL_IPTC_JPG)
        assert res == small_iptc_return

    def test_keywords_tif(self, small_iptc_return):
        res = get_iptc_tags(FULL_IPTC_TIF)
        assert res == small_iptc_return
