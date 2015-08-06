import logging
import os
from TBP import Jpeg, Tiff


logger = logging.getLogger('editor')


def get_wanted_iptc_tags():
    """
       Returns a dictionary of the IPTC Application Record tags

       :return: dictionary
    """
    return {
        'ApplicationRecordVersion': 'ApplicationRecordVersion: mandatory / the current IPTC Information Interchange Model = 4',
        'ObjectTypeReference': 'ObjectTypeReference: 1:News, 2:Data, 3:Advisory x:yy',
        'ObjectAttributeReference': 'ObjectAttributeReference: 1:Current, 2:Analysis, 3: Archive ..x:yy',
        'ObjectName': 'ObjectName: short reference on the object',
        'EditStatus': 'EditStatus: status of the object',
        'EditorialUpdate': 'EditorialUpdate: (To a previous object) x:yyy (Num)',
        'Urgency': 'Urgency: highest is 1, 5 is normal and 8 is lowest',
        'SubjectReference': 'SubjectReference: IPTC:SubRefNum:SubName:SubMatter:SubDetailName',
        'Category': 'Category: not supported anymore,examples: ACE, EDU, SPO for Arts Culture Entertainment,Education,Sport',
        'SupplementalCategories': 'SupplementalCategories: free chosable categories',
        'FixtureIdentifier': 'Fixture Identifier: identifies frequently occuring object data eg "Euroweather"',
        'Keywords': 'Keywords: for in example search purposes',
        'ContentLocationCode': 'ContentLocationCode: 3 char code indicating which country the event took place',
        'ContentLocationName': 'ContentLocationName: Name of the country the event took place',
        'ReleaseDate': 'ReleaseDate: the earliest date the provider intends the object is to be used in format: YYYYMMDD',
        'ReleaseTime': 'ReleaseTime: the earliest time the provider intends the object is to be used in format: HHMMSS +- HHMM [120015+0100]',
        'ExpirationDate': 'ExpirationDate: the latest date the provider intends the object is to be used in format: YYYYMMDD',
        'ExpirationTime': 'ExpirationTime: the latest time the provider intends the object is to be used in format: HHMMSS +- HHMM [120015+0100]',
        'SpecialInstructions': 'SpecialInstructions: further instructions on the object',
        'ActionAdvised': 'ActionAdvised: 2 Digits - provider defined eg 01',
        'ReferenceService': 'ReferenceService: only used to refer to a previous 1:30',
        'ReferenceDate': 'ReferenceDate: only allowed if ReferenceService is used  in format: YYYYMMDD',
        'ReferenceNumber': 'ReferenceNumber: only allowed if ReferenceService is used',
        'DateCreated': 'DateCreated: creation date in format: YYYYMMDD',
        'TimeCreated': 'TimeCreated: creation time in format: HHMMSS +- HHMM [120015+0100]',
        'DigitalCreationDate': 'DigitalCreationDate: date for digitalisation in format: YYYYMMDD',
        'DigitalCreationTime': 'DigitalCreationTime: time for digitalisation in format: HHMMSS +- HHMM [120015+0100]',
        'OriginatingProgram': 'OriginatingProgram: the software used for creation [mediatum]',
        'ProgramVersion': 'ProgramVersion: only use if OriginatingProgram used eg "1.2"',
        'ObjectCycle': 'ObjectCycle: virtually only used in US for Morning Evening or both',
        'By-line': 'By-line: author or photograph',
        'By-lineTitle': 'By-lineTitle: job title',
        'City': 'City: source location of the object',
        'Sub-location': 'Sub-location: district of the location',
        'Province-State': 'Province-State: province',
        'Country-PrimaryLocationCode': 'Country-PrimaryLocationCode: code like in iso 3166 [DE, DEU]',
        'Country-PrimaryLocationName': 'Country-PrimaryLocationName: full name of the country',
        'OriginalTransmissionReference': 'OriginalTransmissionReference: job identifier',
        'Headline': 'Headline: headline',
        'Credit': 'Credit: provider of the object',
        'Source': 'Source: source can differ from creater',
        'CopyrightNotice': 'CopyrightNotice: copyright notice',
        'Contact': 'Contact: contact for further information on the object',
        'Caption-Abstract': 'Caption-Abstract: short description',
        'LocalCaption': 'LocalCaption: local caption',
        'Writer-Editor': 'Writer-Editor: name of the editor',
        'RasterizedCaption': 'RasterizedCaption: rasterized caption',
        'ImageType': 'ImageType: code representing B/w, Y comp of seps',
        'ImageOrientation': 'ImageOrientation: P = Portrait, L = landscape, S = Square',
        'LanguageIdentifier': 'LanguageIdentifier: short code identifying the language',
        'AudioType': 'AudioType: type of the audio',
        'AudioSamplingRate': 'AudioSamplingRate: audio sampling rate',
        'AudioSamplingResolution': 'AudioSamplingResolution: audio sampling resolution',
        'AudioDuration': 'AudioDuration: audio duration',
        'AudioOutcue': 'AudioOutcue: audio octune',
        'JobID': 'JobID: job id',
        'MasterDocumentID': 'MasterDocumentID: master document id',
        'ShortDocumentID': 'ShortDocumentID: short document id',
        'UniqueDocumentID': 'UniqueDocumentID: unique document id',
        'OwnerID': 'OwnerID: owner id',
        'ObjectPreviewFileFormat': 'ObjectPreviewFileFormat: object prieview file format',
        'ObjectPreviewFileVersion': 'ObjectPreviewFileVersion: object preview file version',
        'ObjectPreviewData': 'ObjectPreviewData: object preview data',
        'ClassifyState': 'ClassifyState: classify state',
        'SimilarityIndex': 'SimilarityIndex: similarity index',
        'DocumentNotes': 'DocumentNotes: document notes',
        'DocumentHistory': 'DocumentHistory: document history',
        'ExifCameraInfo': 'ExifCameraInfo: technical camera info'}


def get_iptc_object(file_path):
    """
        returns a itpc object
        for a given path
        (only jpg and tiff are supported)

        :rtype : object
        :param file_path: path to tht file
        :return: iptc object: iptc object to the given path
    """
    if os.path.splitext(file_path)[-1].lower() in ['.jpg', '.jpeg']:
        return Jpeg(file_path)

    elif os.path.splitext(file_path)[-1].lower() in ['.tif', '.tiff']:
        return Tiff(file_path)
    else:
        logger.info('Unsupported file for IPTC reading.')
        return None


def get_iptc_values(file_path):
    """
        get's the IPTC tags/values from a given
        image filepath

        :rtype : object
        :param file_path: path to the desired file
        :return: dictionary with tags
    """
    iptc_object = get_iptc_object(file_path)
    ret = {}
    if iptc_object != {}:
        for tag in get_wanted_iptc_tags():
            try:
                if iptc_object.getIPTCTag(tag):
                    ret[tag] = iptc_object.getIPTCTag(tag)
            except AttributeError as e:
                logging.log('Attribute Error: ', e)
    return ret
