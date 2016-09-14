# -*- coding: utf-8 -*-

from functools import partial
from werkzeug.local import LocalStack, LocalProxy


def _lookup_req_object(name):
    top = _request_ctx_stack.top
    if top is None:
        raise RuntimeError('working outside of request context')
    return getattr(top, name)


def _lookup_current_user():
    from core.users import user_from_session
    top = _request_ctx_stack.top
    if top is None:
        raise RuntimeError('working outside of request context')
    session = top.session
    return user_from_session(session)


def _lookup_app_object(name):
    top = _app_ctx_stack.top
    if top is None:
        raise RuntimeError('working outside of application context')
    return getattr(top, name)


def _find_app():
    top = _app_ctx_stack.top
    if top is None:
        raise RuntimeError('working outside of application context')
    return top.app


# context locals
_request_ctx_stack = LocalStack()
_app_ctx_stack = LocalStack()
current_app = LocalProxy(_find_app)
current_user = LocalProxy(_lookup_current_user)
request = LocalProxy(partial(_lookup_req_object, 'request'))
session = LocalProxy(partial(_lookup_req_object, 'session'))
g = LocalProxy(partial(_lookup_app_object, 'g'))
