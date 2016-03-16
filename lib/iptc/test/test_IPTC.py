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
import pytest
import random
import string
import lib.iptc.IPTC
from core import config
from lib.iptc import IPTC
from utils.date import parse_date
from utils.date import validateDate
from utils.date import format_date


@pytest.fixture
def none_tag_dict():
    return None


@pytest.fixture
def empty_tag_dict():
    return {}


@pytest.fixture
def content_dir():
    ''' returns the test content (images)
        relative directory
    '''
    return '{}/test_iptc/test_data/'.format(config.basedir)


@pytest.fixture
def empty_iptc_tif(content_dir):
    return '{}{}'.format(content_dir,'empty.tif')


@pytest.fixture
def empty_iptc_jpg(content_dir):
    return '{}{}'.format(content_dir,'empty.jpg')


@pytest.fixture
def date_tif(content_dir):
    return '{}{}'.format(content_dir, 'date.tif')


@pytest.fixture
def date_jpg(content_dir):
    return '{}{}'.format(content_dir, 'date.jpg')


@pytest.fixture
def random_jpg(content_dir):
    return '{}{}'.format(content_dir, 'random.jpg')


@pytest.fixture
def random_tif(content_dir):
    return '{}{}'.format(content_dir, 'random.tif')


@pytest.fixture
def keywords_jpg(content_dir):
    return '{}{}'.format(content_dir, 'keywords_list.jpg')


@pytest.fixture
def keywords_tif(content_dir):
    return '{}{}'.format(content_dir, 'keywords_list.tif')

@pytest.fixture
def write_ascii_jpg(content_dir):
    return '{}{}'.format(content_dir, 'write_ascii.jpg')


@pytest.fixture
def write_ascii_tif(content_dir):
    return '{}{}'.format(content_dir, 'write_ascii.tif')


@pytest.fixture
def write_unicode_jpg(content_dir):
    return '{}{}'.format(content_dir, 'write_unicode.jpg')


@pytest.fixture
def write_unicode_tif(content_dir):
    return '{}{}'.format(content_dir, 'write_unicode.tif')


@pytest.fixture
def iptc_Keywords():
    return {'iptc_Keywords': '1;2;3'}


@pytest.fixture
def less_tags():
    return {
        'iptc_ApplicationRecordVersion': 'ApplicationRecordVersion |5',
        'iptc_Caption-Abstract': 'Caption-Abstract |2000',
        'iptc_By-line': 'By-line |32',
        'iptc_Keywords': 'Keywords |64',
        'iptc_City': 'City |32'
    }


@pytest.fixture
def small_iptc_tif_return():
    return \
    {
        'iptc_ApplicationRecordVersion': 4,
        'iptc_Keywords': '1;2;3'
    }


@pytest.fixture
def small_iptc_jpg_return():
    return \
    {
        'iptc_ApplicationRecordVersion': 4,
        'iptc_Keywords': '1;2;3'
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
            'iptc_ApplicationRecordVersion': 4,
            'iptc_Caption-Abstract': 'abstract'
           }


@pytest.fixture
def write_dict():
    return {
            'Caption-Abstract': 'abstract'
           }


#can't use fixures in mark.parametrized bug #349 py.test (github)
CONTENT_DIR = '{}/test_iptc/test_data/'.format(config.basedir)

EMPTY_IPTC_TIF = '{}{}'.format(CONTENT_DIR,'empty.tif')
EMPTY_IPTC_JPG = '{}{}'.format(CONTENT_DIR,'empty.jpg')

FULL_IPTC_TIF = '{}{}'.format(CONTENT_DIR,'keywords_list.tif')
FULL_IPTC_JPG = '{}{}'.format(CONTENT_DIR,'keywords_list.jpg')

DATE_JPG = '{}{}'.format(CONTENT_DIR, 'date.jpg')
RANDOM_TIF = '{}{}'.format(CONTENT_DIR, 'random.tif')


def rand_unicode():
    ''' generates some random
        unicode string (of course not all u ;)
    '''
    b = ['03','30'] #?
    l = ''.join([random.choice('ABCDEF0123456789') for x in xrange(2)])
    return unichr(random.choice((0x300, 0x2000)) + random.randint(0, 0xff))


def str_gen(size=6, chars= '{}{}'.format(string.ascii_uppercase, string.digits)):
    ''' generates a random string
        with a desired lenth
        according to security (not needed)
        SystemRandom is not to be used
    '''
    return ''.join(random.choice(chars) for _ in range(size))

class TestGetWanted_testValues:
    ''' tests the exact value returned
        by lib.iptc.IPTC.get_wanted_tags
        and test iptc values read from file
    '''
    @classmethod
    def setup_class(cls):
        cls.iptc_tags = {
        'iptc_ActionAdvised': 'ActionAdvised |2',
        'iptc_ApplicationRecordVersion': 'ApplicationRecordVersion |5',
        'iptc_AudioType': 'AudioType |2',
        'iptc_AudioSamplingRate': 'AudioSamplingRate |6',
        'iptc_AudioSamplingResolution': 'AudioSamplingResolution |2',
        'iptc_AudioDuration': 'AudioDuration |6',
        'iptc_AudioOutcue': 'AudioOutcue |64',
        'iptc_By-line': 'By-line |32',
        'iptc_By-lineTitle': 'By-lineTitle |32',
        'iptc_Caption-Abstract': 'Caption-Abstract |2000',
        'iptc_CatalogSets': 'CatalogSets |256',
        'iptc_Category': 'Category |3',
        'iptc_City': 'City |32',
        'iptc_ClassifyState': 'ClassifyState |64',
        'iptc_Contact': 'Contact |128',
        'iptc_ContentLocationCode': 'ContentLocationCode |3',
        'iptc_ContentLocationName': 'ContentLocationName |64',
        'iptc_Country-PrimaryLocationCode': 'Country-PrimaryLocationCode |3',
        'iptc_Country-PrimaryLocationName': 'Country-PrimaryLocationName |64',
        'iptc_CopyrightNotice': 'CopyrightNotice |128',
        'iptc_Credit': 'Credit |32',
        'iptc_DateCreated': 'DateCreated |8',
        'iptc_DocumentNotes': 'DocumentNotes |1024',
        'iptc_DocumentHistory': 'DocumentHistory |256',
        'iptc_DigitalCreationDate': 'DigitalCreationDate |8',
        'iptc_DigitalCreationTime': 'DigitalCreationTime |11',
        'iptc_EditStatus': 'EditStatus |64',
        'iptc_EditorialUpdate': 'EditorialUpdate |2',
        'iptc_ExifCameraInfo': 'ExifCameraInfo |4096',
        'iptc_ExpirationDate': 'ExpirationDate |8',
        'iptc_ExpirationTime': 'ExpirationTime |11',
        'iptc_FixtureIdentifier': 'FixtureIdentifier |32',
        'iptc_Headline': 'Headline |256',
        'iptc_ImageType': 'ImageType |2',
        'iptc_ImageOrientation': 'ImageOrientation |1',
        'iptc_JobID': 'JobID |64',
        'iptc_Keywords': 'Keywords |64',
        'iptc_LanguageIdentifier': 'LanguageIdentifier |3',
        'iptc_LocalCaption': 'LocalCaption |256',
        'iptc_MasterDocumentID': 'MasterDocumentID |256',
        'iptc_ObjectAttributeReference': 'ObjectAttributeReference |68',
        'iptc_ObjectCycle': 'ObjectCycle |1',
        'iptc_ObjectName': 'ObjectName |64',
        'iptc_ObjectPreviewFileFormat': 'ObjectPreviewFileFormat |29',
        'iptc_ObjectPreviewFileVersion': 'ObjectPreviewFileVersion |5',
        'iptc_ObjectPreviewData': 'ObjectPreviewData |256000',
        'iptc_ObjectTypeReference': 'ObjectTypeReference |67',
        'iptc_OriginalTransmissionReference': 'OriginalTransmissionReference |32',
        'iptc_OriginatingProgram': 'OriginatingProgram |32',
        'iptc_OwnerID': 'OwnerID |128',
        'iptc_Prefs': 'Prefs |64',
        'iptc_ProgramVersion': 'ProgramVersion |10',
        'iptc_Province-State': 'Province-State |32',
        'iptc_RasterizedCaption': 'RasterizedCaption |7360',
        'iptc_ReferenceService': 'ReferenceService |10',
        'iptc_ReferenceDate': 'ReferenceDate |8',
        'iptc_ReferenceNumber': 'ReferenceNumber |8',
        'iptc_ReleaseDate': 'ReleaseDate |8',
        'iptc_ReleaseTime': 'ReleaseTime |11',
        'iptc_SimilarityIndex': 'SimilarityIndex |32',
        'iptc_ShortDocumentID': 'ShortDocumentID |64',
        'iptc_SpecialInstructions': 'SpecialInstructions |256',
        'iptc_SubjectReference': 'SubjectReference |236',
        'iptc_Sub-location': 'Sub-location |32',
        'iptc_Source': 'Source |32',
        'iptc_SupplementalCategories': 'SupplementalCategories |32',
        'iptc_TimeCreated': 'TimeCreated |11',
        'iptc_Urgency': 'Urgency |1',
        'iptc_UniqueDocumentID': 'UniqueDocumentID |128',
        'iptc_Writer-Editor': 'Writer-Editor |32'
        }

    def test_get_wanted_iptc_tags(self):
        assert lib.iptc.IPTC.get_wanted_iptc_tags() == self.iptc_tags

    def test_get_iptc_values_tif(self, small_iptc_tif_return):
        assert lib.iptc.IPTC.get_iptc_values(FULL_IPTC_TIF, self.iptc_tags) == small_iptc_tif_return

    def test_get_iptc_values_jpg(self, small_iptc_jpg_return):
        assert lib.iptc.IPTC.get_iptc_values(FULL_IPTC_JPG, self.iptc_tags) == small_iptc_jpg_return


class TestEmptyFilePathes():
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
        assert lib.iptc.IPTC.get_iptc_values(file_path, less_tags) == expected

    @pytest.mark.parametrize("file_path, expected",
    [
        (None, None),
        ('', None),
        ('-', None),
        (EMPTY_IPTC_JPG, {})
    ])
    def test_iptc_values_empty_jpg(self, less_tags, file_path, expected):
        assert lib.iptc.IPTC.get_iptc_values(file_path, less_tags) == expected


class TestEmptyIPTCValues:
    ''' tests for empty iptc
    '''
    def test_iptc_values_empty_tif(self, empty_iptc_tif, less_tags):
        assert lib.iptc.IPTC.get_iptc_values(empty_iptc_tif, less_tags) == {}

    def test_iptc_values_empty_jpg(self, empty_iptc_jpg, less_tags):
        assert lib.iptc.IPTC.get_iptc_values(empty_iptc_jpg, less_tags) == {}


class TestIsoDate:
    def test_iso_date_jpg(self, date_jpg, iso_date):
        assert parse_date(IPTC.get_iptc_values(date_jpg, IPTC.get_wanted_iptc_tags())['iptc_DateCreated'], format='%Y:%m:%d').__str__() == iso_date

    def test_iso_date_tif(self, date_tif, iso_date):
        assert parse_date(IPTC.get_iptc_values(date_tif, IPTC.get_wanted_iptc_tags())['iptc_DateCreated'], format='%Y:%m:%d').__str__() == iso_date


class TestWriteIPTC:
    def test_write_jpg(self, less_tags, write_dict, read_dict, random_jpg):
        lib.iptc.IPTC.write_iptc_tags(random_jpg, write_dict)
        assert lib.iptc.IPTC.get_iptc_values(random_jpg, less_tags) == read_dict

    def test_write_tif(self, less_tags, write_dict, read_dict, random_tif):
        lib.iptc.IPTC.write_iptc_tags(random_tif, write_dict)
        assert lib.iptc.IPTC.get_iptc_values(random_tif, less_tags) == read_dict

    def test_write_acii(self, write_ascii_jpg, write_ascii_tif):
        rnd_ascii = str_gen(2000)

        tag_dict = {'Caption-Abstract': u'{}'.format(rnd_ascii)}
        lib.iptc.IPTC.write_iptc_tags(write_ascii_jpg, tag_dict)
        lib.iptc.IPTC.write_iptc_tags(write_ascii_tif, tag_dict)

        ret_dict_jpg = lib.iptc.IPTC.get_iptc_values(write_ascii_jpg, lib.iptc.IPTC.get_wanted_iptc_tags())
        ret_dict_tif = lib.iptc.IPTC.get_iptc_values(write_ascii_tif, lib.iptc.IPTC.get_wanted_iptc_tags())

        assert ret_dict_jpg['iptc_Caption-Abstract'] == rnd_ascii
        assert ret_dict_tif['iptc_Caption-Abstract'] == rnd_ascii

    def test_write_acii_tags(self, write_ascii_jpg, write_ascii_tif):
        tags = lib.iptc.IPTC.get_wanted_iptc_tags()

        for tag in tags:
            choice_tag = random.choice(tags.keys())
            if int(tags[choice_tag].split('|')[-1]) > 127:
                str_len = int(tags[choice_tag].split('|')[-1])
                break

        rnd_ascii = str_gen(str_len)

        tag_dict = {'{}'.format(choice_tag.split('iptc_')[-1]): u'{}'.format(rnd_ascii)}

        lib.iptc.IPTC.write_iptc_tags(write_ascii_jpg, tag_dict)
        lib.iptc.IPTC.write_iptc_tags(write_ascii_tif, tag_dict)

        ret_dict_jpg = lib.iptc.IPTC.get_iptc_values(write_ascii_jpg, lib.iptc.IPTC.get_wanted_iptc_tags())
        ret_dict_tif = lib.iptc.IPTC.get_iptc_values(write_ascii_tif, lib.iptc.IPTC.get_wanted_iptc_tags())

        assert ret_dict_jpg[choice_tag] == rnd_ascii
        assert ret_dict_tif[choice_tag] == rnd_ascii

    def test_write_unicode(self, write_unicode_jpg, write_unicode_tif):
        ''' writes a single unicode char into a jpg and tif
            image and compares the read solutions by
            according to available unicode codepoints
            random sequenzes of generated unicode
            strings could not be checked
        '''
        rnd_unicode = rand_unicode()
        write_unicode_jpg = '/home/berckner/mediatum-postgres/test_iptc/test_data/write_unicode.jpg'

        lib.iptc.IPTC.write_iptc_tags(write_unicode_jpg, {'Caption-Abstract': u'{}'.format(rnd_unicode)})
        lib.iptc.IPTC.write_iptc_tags(write_unicode_tif, {'Caption-Abstract': u'{}'.format(rnd_unicode)})

        ret_dict = lib.iptc.IPTC.get_iptc_values(write_unicode_jpg, lib.iptc.IPTC.get_wanted_iptc_tags())

        assert ret_dict['iptc_Caption-Abstract'].encode('utf-8') == rnd_unicode.encode('utf-8')
        assert ret_dict['iptc_Caption-Abstract'].encode('utf-8') == rnd_unicode.encode('utf-8')


class TestIPTCKeywords:
    def test_keywords_jpg(sel, keywords_jpg, keywords_tif, small_iptc_jpg_return, small_iptc_tif_return):
        ''' test for keywords section
            keywords seperated by
            semicolon for
            indexing
        '''
        assert lib.iptc.IPTC.get_iptc_values(keywords_jpg, lib.iptc.IPTC.get_wanted_iptc_tags()) == small_iptc_jpg_return
        assert lib.iptc.IPTC.get_iptc_values(keywords_tif, lib.iptc.IPTC.get_wanted_iptc_tags()) == small_iptc_tif_return