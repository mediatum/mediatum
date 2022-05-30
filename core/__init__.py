# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

__version__ = "v2020.04"

# set by core.database
db = None
# set by core.init.init_app()
app = None

# TODO: move to web.edit
editmodulepaths = [('', 'web/edit/modules')]

import utils.log
