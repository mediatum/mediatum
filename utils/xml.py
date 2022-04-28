# -*- coding: utf-8 -*-

# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import re

RE_ILLEGAL_CHAR = re.compile(u'[^\u0020-\uD7FF\u0009\u000A\u000D\uE000-\uFFFD\u10000-\u10FFFF]+', re.UNICODE)

def xml_remove_illegal_chars(s):
    return RE_ILLEGAL_CHAR.sub(u"", s)
