# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from sqlalchemy import Column, ForeignKey, Index, Integer, Unicode
from sqlalchemy_utils.types.ts_vector import TSVectorType

from core.db.postgres import DeclarativeBase

C = Column
FK = ForeignKey


class NodeSearch(DeclarativeBase):
    __tablename__ = "nodesearch"
    nid = C(Integer, FK("node.id"), primary_key=True, index=True)
    lang = C(Unicode(255), primary_key=True)
    fulltext_search = C(TSVectorType)
