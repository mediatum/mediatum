# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import logging
import os
import hashlib
from core import db

q = db.query
logg = logging.getLogger(__name__)


def calcChecksum(filename, method):
    if os.path.exists(filename):
        f = open(filename)
        if method == "SHA-1":
            h = hashlib.sha1()
        else:
            h = hashlib.new('ripemd160')
        h.update(f.read())
        f.close()
        return h.hexdigest()
    else:
        return ""


def calcChecksumFromMetadata(node):
    h = hashlib.sha1()
    h.update(str(node.id))  # h.update requires string or buffer as argument
    h.update(node.getName())

    def attributesToString(node):
        string = ""
        for item in node.attrs.items():
            string += item[0] + item[1]
        return string

    h.update(attributesToString(node))

    return h.hexdigest()
