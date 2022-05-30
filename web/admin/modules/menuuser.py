# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function


def getInformation(attribute=""):
    attributes = {"icon": "/img/icons/usergroups.gif",
                  "version": "1.0"}
    if attribute != "":
        if attribute in attributes.keys():
            return attributes[attribute]
        else:
            return ""
    return attributes


def validate(req, op):
    return "dummymenu"
