# -*- coding: utf-8 -*-

# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

from sqlalchemy import Unicode
from sqlalchemy.dialects.postgresql.json import JSONB
from core.database.postgres import DeclarativeBase, C


class Setting(DeclarativeBase):

    """Key-value pair for mediaTUM settings that can be changed at runtime"""

    __tablename__ = "setting"

    key = C(Unicode, primary_key=True)
    value = C(JSONB)
