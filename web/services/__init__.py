# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2016 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from __future__ import division

import json
import logging
import datetime

import core.config as config
from core import httpstatus
from utils.log import make_xid_and_errormsg_hash
from functools import wraps

logg = logging.getLogger(__name__)

TESTING = config.get("host.type") == "testing"


template_exception2xml = u'''
<?xml version='1.0' encoding='utf8'?>
<response status="fail" retrievaldate="%(iso_datetime_now)s">
  <errormsg>%(errormsg)s</errormsg>
</response>
'''

template_exception2json = json.dumps({"status": "fail",
                              "retrievaldate": "%(iso_datetime_now)s",
                              "errormsg": "%(errormsg)s",
                              })

template_exception2csv = u'errormsg\n%(errormsg)s'

template_exception2template_test = template_exception2csv

template_exception2rss = template_exception2xml

# {'format_name': [template, mime-type]}
supported_formats = { 'xml': [template_exception2xml, 'text/xml'],
    'json': [template_exception2json, 'application/json'],
    'csv': [template_exception2csv, 'text/csv'],
    'template_test': [template_exception2template_test, 'text/plain'],
    'rss': [template_exception2rss, 'application/rss+xml'],
}


def dec_handle_exception(func):
    if TESTING:
        return func
    @wraps(func)
    def wrapper(req):
        try:
            http_status_code = func(req)
            return http_status_code
        except Exception, e:
            iso_datetime_now = datetime.datetime.now().isoformat()
            xid, hashed_errormsg, hashed_tb = make_xid_and_errormsg_hash()
            
            logg.exception(u"exception (xid=%s) while handling request %s %s, %s", 
                           xid, req.method, req.mediatum_contextfree_path, dict(req.args))

            response_format = req.params.get('format', '').lower()
            response_template, response_mimetype = supported_formats.get(response_format, supported_formats.get('xml'))
            response = response_template % dict(iso_datetime_now=iso_datetime_now, errormsg=xid)
            response = response.strip()  # remove whitespaces at least from xml response
            req.response.content_type = response_mimetype
            req.response.status_code = httpstatus.HTTP_INTERNAL_SERVER_ERROR
            req.response.set_data(response)
            return None  # do not send status code 500, ..., athana would overwrite response
    return wrapper
