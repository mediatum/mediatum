# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
This module completely initializes mediaTUM
"""

from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from itertools import imap as map
from itertools import ifilter as filter
range = xrange

import os as _os
import sys as _sys
_sys.path.append(_os.path.abspath(_os.path.join(__file__, "..", "..")))

import core.init as _core_init

_core_init.full_init()
