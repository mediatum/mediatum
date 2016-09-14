# -*- coding: utf-8 -*-
"""
Let's do some test testing ;)
"""


def test_session(session):
    """Tests if the session rolls back correctly and leaves no traces. Assert is in the fixture."""
    from core import Node
    session.add(Node(u"name"))


def test_session_commit(session):
    """Tests if the session rolls back correctly and leaves no traces, even after a commit."""
    from core import Node
    session.add(Node(u"name"))
    session.commit()


def test_session_commit2(session):
    """Tests if the session rolls back correctly and leaves no traces, even after two commits..."""
    from core import Node
    session.add(Node(u"name"))
    session.commit()
    session.commit()


def test_session_rollback(session):
    """Tests if the session fixture works even after a rollback and commit..."""
    from core import Node
    session.add(Node(u"name"))
    session.rollback()
    session.commit()