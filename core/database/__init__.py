# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from core.database.postgres.connector import PostgresSQLAConnector

import core
# default connector is postgres, no choice at the moment ;)
core.db = PostgresSQLAConnector()