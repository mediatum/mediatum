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
import sys
sys.path.append('.')
import logging
import os
import subprocess
import exiftool
from utils.date import parse_date
from utils.date import validateDate
from utils.date import format_date
from utils.strings import ensure_unicode
from core import config
import utils.process
import collections


logg = logging.getLogger(__name__)


def get_wanted_iptc_tags():
    '''
        Returns a dictionary [Tagname:size]
        from supported IPTC tags.
        :return: dictionary
    '''
    return collections.OrderedDict(sorted({
        'ActionAdvised': 'ActionAdvised |2',
        'ApplicationRecordVersion': 'ApplicationRecordVersion |5',
        'AudioType': 'AudioType |2',
        'AudioSamplingRate': 'AudioSamplingRate |6',
        'AudioSamplingResolution': 'AudioSamplingResolution |2',
        'AudioDuration': 'AudioDuration |6',
        'AudioOutcue': 'AudioOutcue |64',
        'By-line': 'By-line |32',
        'By-lineTitle': 'By-lineTitle |32',
        'Caption-Abstract': 'Caption-Abstract |2000',
        'CatalogSets': 'CatalogSets |256',
        'Category': 'Category |3',
        'City': 'City |32',
        'ClassifyState': 'ClassifyState |64',
        'Contact': 'Contact |128',
        'ContentLocationCode': 'ContentLocationCode |3',
        'ContentLocationName': 'ContentLocationName |64',
        'Country-PrimaryLocationCode': 'Country-PrimaryLocationCode |3',
        'Country-PrimaryLocationName': 'Country-PrimaryLocationName |64',
        'CopyrightNotice': 'CopyrightNotice |128',
        'Credit': 'Credit |32',
        'DateCreated': 'DateCreated |8',
        'DocumentNotes': 'DocumentNotes |1024',
        'DocumentHistory': 'DocumentHistory |256',
        'DigitalCreationDate': 'DigitalCreationDate |8',
        'DigitalCreationTime': 'DigitalCreationTime |11',
        'EditStatus': 'EditStatus |64',
        'EditorialUpdate': 'EditorialUpdate |2',
        'ExifCameraInfo': 'ExifCameraInfo |4096',
        'ExpirationDate': 'ExpirationDate |8',
        'ExpirationTime': 'ExpirationTime |11',
        'FixtureIdentifier': 'FixtureIdentifier |32',
        'Headline': 'Headline |256',
        'ImageType': 'ImageType |2',
        'ImageOrientation': 'ImageOrientation |1',
        'JobID': 'JobID |64',
        'Keywords': 'Keywords |64',
        'LanguageIdentifier': 'LanguageIdentifier |3',
        'LocalCaption': 'LocalCaption |256',
        'MasterDocumentID': 'MasterDocumentID |256',
        'ObjectAttributeReference': 'ObjectAttributeReference |68',
        'ObjectCycle': 'ObjectCycle |1',
        'ObjectName': 'ObjectName |64',
        'ObjectPreviewFileFormat': 'ObjectPreviewFileFormat |29',
        'ObjectPreviewFileVersion': 'ObjectPreviewFileVersion |5',
        'ObjectPreviewData': 'ObjectPreviewData |256000',
        'ObjectTypeReference': 'ObjectTypeReference |67',
        'OriginalTransmissionReference': 'OriginalTransmissionReference |32',
        'OriginatingProgram': 'OriginatingProgram |32',
        'OwnerID': 'OwnerID |128',
        'Prefs': 'Prefs |64',
        'ProgramVersion': 'ProgramVersion |10',
        'Province-State': 'Province-State |32',
        'RasterizedCaption': 'RasterizedCaption |7360',
        'ReferenceService': 'ReferenceService |10',
        'ReferenceDate': 'ReferenceDate |8',
        'ReferenceNumber': 'ReferenceNumber |8',
        'ReleaseDate': 'ReleaseDate |8',
        'ReleaseTime': 'ReleaseTime |11',
        'SimilarityIndex': 'SimilarityIndex |32',
        'ShortDocumentID': 'ShortDocumentID |64',
        'SpecialInstructions': 'SpecialInstructions |256',
        'SubjectReference': 'SubjectReference |236',
        'Sub-location': 'Sub-location |32',
        'Source': 'Source |32',
        'SupplementalCategories': 'SupplementalCategories |32',
        'TimeCreated': 'TimeCreated |11',
        'Urgency': 'Urgency |1',
        'UniqueDocumentID': 'UniqueDocumentID |128',
        'Writer-Editor': 'Writer-Editor |32'
    }.items()))


def get_iptc_tags(image_path, tags=None):
    """
        get the IPTC tags/values from a given
        image file

        :rtype : object
        :param image_path: path to the image file
        :param tags: dictionary with wanted iptc tags
        :return: dictionary with tag/value
    """
    if tags == None:
        tags = get_wanted_iptc_tags()

    if not isinstance(tags, dict):
        logg.warn('No Tags to read.')
        return

    if image_path is None:
        logg.warn('No file path for reading iptc.')
        return

    if not os.path.exists(image_path):
        logg.warn('Could not read IPTC metadata from non existing file.')
        return

    if os.path.basename(image_path).startswith('-'):
        logg.warn('Will not read IPTC metadata to files starting with a hyphen, caused by exiftool security issues.')
        return

    # fetch metadata dict from exiftool
    exiftool_exe = config.get("external.exiftool", "exiftool")
    with exiftool.ExifTool(exiftool_exe) as et:
        iptc_metadata = et.get_metadata(image_path)

    ret = {}

    for iptc_tag in tags.keys():
        key = "IPTC:" + iptc_tag
        if key in iptc_metadata:
            value = iptc_metadata[key]

            # format dates for date fields
            if iptc_tag == 'DateCreated':
                if validateDate(parse_date(value, format='%Y:%m:%d')):
                    value = format_date(parse_date(value, format='%Y:%m:%d'))
                else:
                    logg.error('Could not validate: {} as date value.'.format(value))

            # join lists to strings
            if isinstance (value, list):
                value = ';'.join(ensure_unicode(e, silent=True) for e in value)

            ret[iptc_tag] = ensure_unicode(value, silent=True)

    logg.info('{} read from file.'.format(ret))

    return ret


def write_iptc_tags(image_path, tag_dict):
    '''
        Writes iptc tags with exiftool to a
        given image path (overwrites the sourcefile).
        Emty tags (tagname='') will be removed.

        :param image_path: imaqe path to write
        :param tag_dict: tagname / tagvalue

        :return  status
    '''
    try:
        utils.process.call(['exiftool'])
    except OSError:
        logg.error('No exiftool installed.')
        return

    image_path = os.path.abspath(image_path)

    if not os.path.exists(image_path):
        logg.info(u'Image {} for writing IPTC metadata does not exist.'.format(image_path))
        return

    if not isinstance(tag_dict, dict):
        logg.error(u'No dictionary of tags.')
        return

    command_list = [u'exiftool']
    command_list.append(u'-overwrite_original')

    command_list.append(u'-charset')
    command_list.append(u'iptc=UTF8')

    command_list.append(image_path)

    for tag_name in tag_dict.keys():
        tag_value = tag_dict[tag_name]

        if tag_dict[tag_name] == '':
            command_list.append(u'-{}='.format(tag_name))

        elif tag_name == u'DateCreated':
            if validateDate(parse_date(tag_value.split('T')[0], format='%Y-%m-%d')):
                tag_value = format_date(parse_date(tag_value.split('T')[0], format='%Y-%m-%d'), '%Y:%m:%d')
            else:
                logg.error(u'Could not validate {}.'.format(tag_value))

        command_list.append(u'-charset iptc=UTF8')
        command_list.append(u'-{}={}'.format(tag_name, tag_value))

    logg.info(u'Command: {} will be executed.'.format(command_list))
    process = utils.process.Popen(command_list, stdout=subprocess.PIPE)
    output, error = process.communicate()

    if error is not None:
        logg.info('Exiftool output: {}'.format(output))
        logg.error('Exiftool error: {}'.format(error))
