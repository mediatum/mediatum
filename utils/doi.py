# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import httplib2
import base64
import codecs
import logging
import os
import core.config as config
from core import Node
from core import db
from schema.schema import getMetaType, Metadatatype

q = db.query
logg = logging.getLogger(__name__)


def generate_doi_test(node):
    """
    @param node
    Returns a DOI for the given node for testing purposes
    """
    prefix = config.get('doi.prefix_test')
    node_id = unicode(node.id)

    return u'/'.join([prefix, node_id])


def generate_doi_live(node):
    """
    @param node
    Returns a doi for the given node
    """
    prefix = config.get('doi.prefix_live')
    suffix = config.get('doi.suffix')

    # strips suffix if not declared or set empty
    if suffix is None:
        suffix = ''

    params = {
        'year': '',
        'publisher': config.get('doi.publisher'),
        'type': '',
        'id': node.id,
    }

    possible_year_fields = [
        'year',
        'year-accepted',
        'sv-year',
        'event-date',
        'creationtime',
        'date-start',
        'time-created',
        'pdf_creationdate',
        'date-end',
        'ingested',
        'updatetime',
        'updatesearchindex'
    ]

    for field in possible_year_fields:
        if field in node.attributes:
            params['year'] = node.get(field)[:4]
            break

    if node.getContentType() not in ('document', 'image'):
        raise Exception('document type not document or image but rather {}'.format(node.type))
    else:
        params['type'] = node.type

    return '10.{}/{}{}{}{}/{}'.format(prefix,
                                      params['year'],
                                      params['publisher'],
                                      params['type'],
                                      params['id'],
                                      suffix).rstrip('/')


def create_meta_file(node):
    """
    @param node
    Creates and returns the path to the 'metadata file' needed to register the doi with datacite via api
    """
    if 'doi' not in node.attributes:
        raise Exception('doi not set')
    else:
        tmp = config.get('paths.tempdir')
        filename = 'meta_file_{}.txt'.format(node.id)
        path = os.path.join(tmp, filename)

        if os.path.exists(path):
            pass
        else:
            try:
                with codecs.open(path, 'w', encoding='utf8') as f:
                    mask = q(Metadatatype).filter_by(name=node.schema).scalar().get_mask('doi')
                    xml = mask.getViewHTML([node], flags=8)
                    f.write(xml)
            except AttributeError:
                logg.error(
                    'Doi was not successfully registered: Doi-mask for Schema %s is missing and should be created',
                    node.schema)
                del node.attrs['doi']
            except IOError:
                logg.exception('Error creating %s', path)

        return path


def create_doi_file(node):
    """
    @param node
    Creates and returns the path to the 'doi file' needed to register the doi with datacite via api
    """
    if 'doi' not in node.attrs:
        raise Exception('doi not set')
    else:
        tmp = config.get('paths.tempdir')
        host = config.get('host.name')
        filename = 'doi_file_{}.txt'.format(node.id)
        path = os.path.join(tmp, filename)

        if os.path.exists(path):
            pass
        else:
            try:
                with codecs.open(path, 'w', encoding='utf8') as f:
                    f.write('doi={}\n'.format(node.get('doi')))
                    f.write('url={}{}{}{}'.format('http://',
                                                  'mediatum.ub.tum.de',
                                                  '/?id=',
                                                  node.id))
            except IOError:
                logg.exception('Error creating %s', path)
        return path


def post_file(file_type, file_location):
    """
    @param file_type is either 'doi' or 'metadata'
    @param file_location is the path to the metadata or doi file
    Posts the given file via datacite api to their servers and returns the response and content.
    """
    if all(file_type != i for i in ('doi', 'metadata')):
        raise Exception('file_type needs to be either "doi" or "metadata"')

    endpoint = 'https://mds.datacite.org/' + file_type
    auth = base64.encodestring(config.get('doi.username') + ':' + config.get('doi.password'))
    header = {'Content-Type': '',
              'Authorization': 'Basic ' + auth}

    if file_type == 'doi':
        header['Content-Type'] = 'text/plain;charset=UTF-8'
    if file_type == 'metadata':
        header['Content-Type'] = 'application/xml;charset=UTF-8'

    msg = codecs.open(file_location,
                      'r',
                      encoding='UTF-8').read()
    h = httplib2.Http()

    response, content = h.request(endpoint, 'POST', body=msg.encode('utf-8'), headers=header)

    return response.status, content.encode('utf-8')
