# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from sqlalchemy import Unicode
from sqlalchemy.dialects.postgresql.json import JSONB
from core.database.postgres import DeclarativeBase, C


class Setting(DeclarativeBase):

    """Key-value pair for mediaTUM settings that can be changed at runtime"""

    __tablename__ = "setting"

    key = C(Unicode, primary_key=True)
    value = C(JSONB)
