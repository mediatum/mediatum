# -*- coding: utf-8 -*-
'''
HTTP status codes from athana used by mediaTUM
'''
from __future__ import division

import string as _string
HTTP_OK = 200
HTTP_MOVED_TEMPORARILY = HTTP_FOUND = 302
HTTP_TEMPORARY_REDIRECT = 307
HTTP_BAD_REQUEST = 400
HTTP_FORBIDDEN = 403
HTTP_NOT_FOUND = 404
HTTP_NOT_ACCEPTABLE = 406
HTTP_INTERNAL_SERVER_ERROR = 500
responses = {
    100: "Continue",
    101: "Switching Protocols",
    200: "OK",
    201: "Created",
    202: "Accepted",
    203: "Non-Authoritative Information",
    204: "No Content",
    205: "Reset Content",
    206: "Partial Content",
    300: "Multiple Choices",
    301: "Moved Permanently",
    302: "Moved Temporarily",
    303: "See Other",
    304: "Not Modified",
    305: "Use Proxy",
    307: "Temporary Redirect",
    400: "Bad Request",
    401: "Unauthorized",
    402: "Payment Required",
    403: "Forbidden",
    404: "Not Found",
    405: "Method Not Allowed",
    406: "Not Acceptable",
    407: "Proxy Authentication Required",
    408: "Request Time-out",
    409: "Conflict",
    410: "Gone",
    411: "Length Required",
    412: "Precondition Failed",
    413: "Request Entity Too Large",
    414: "Request-URI Too Large",
    415: "Unsupported Media Type",
    418: "I'm a Teapot",
    500: "Internal Server Error",
    501: "Not Implemented",
    502: "Bad Gateway",
    503: "Service Unavailable",
    504: "Gateway Time-out",
    505: "HTTP Version not supported",
    506: "CSRF token missing",
    507: "CSRF failed",
}

# Default error message
DEFAULT_ERROR_MESSAGE = _string.join(
    ['<html><head>',
     '<title>Error response</title>',
     '</head>',
     '<body>',
     '<h1>Error response</h1>',
     '<p>Error code %(code)d.</p>',
     '<p>Message: %(message)s.</p>',
     '</body></html>',
     ''
     ],
    '\r\n'
)
