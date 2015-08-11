# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""

from core import db
from pytest import fixture, mark
q = db.query


@fixture
def documents_1000(session):
    from contenttypes import Document
    docs = [Document(str(i), attrs={"num": i}) for i in xrange(1000)]
    session.add_all(docs)
    session.commit()
    return docs


@mark.slow
def test_insert():
    from contenttypes import Document
    count = 1000
    docs = [Document(str(i), attrs={"num": i}) for i in xrange(1000)]
    db.session.add_all(docs)
    db.session.commit()
    db
    assert q(Document).count() == count
    
    
@mark.slow
def test_modify(session, documents_1000):
    for num, doc in enumerate(documents_1000):
        doc["num"] = 1000 + num 
    session.commit()