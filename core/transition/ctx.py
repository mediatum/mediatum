# -*- coding: utf-8 -*-

from __future__ import division, absolute_import, print_function

import logging
from core.transition.globals import _app_ctx_stack, _request_ctx_stack
from core.transition.helpers import runswith


logg = logging.getLogger(__name__)


class _AppCtxGlobals(object):

    """A plain object."""

    def get(self, name, default=None):
        return self.__dict__.get(name, default)

    def __contains__(self, item):
        return item in self.__dict__

    def __iter__(self):
        return iter(self.__dict__)

    def __repr__(self):
        top = _app_ctx_stack.top
        if top is not None:
            return '<athana_flask.g of %r, id %s>' % (top.app.name, id(top.app))
        return object.__repr__(self)


class AthanaRequestAdapter(object):

    def __init__(self, athana_request):
        self._athana_request = athana_request

    def __getattr__(self, name):
        return getattr(self._athana_request, name)

    def __setattr__(self, name, value):
        setattr(self._athana_request, name, value)


class RequestContext(object):

    def __init__(self, app, request, session):
        self.request = request
        self.session = session
        self.app = app
        self._implicit_app_ctx_stack = []

    if runswith == "athana":
        def request_adapter(self, request):
            return AthanaRequestAdapter(request)
    else:
        def request_adapter(self, request):
            return request

    def __enter__(self):
        self.push()
        return self

    def __exit__(self, exc_type, exc_value, tb):
        # do not pop the request stack if we are in debug mode and an
        # exception happened.  This will allow the debugger to still
        # access the request object in the interactive shell.  Furthermore
        # the context can be force kept alive for the test client.
        # See flask.testing for how this works.
        self.pop(exc_value)

    def push(self):
        # Before we push the request context we have to ensure that there
        # is an application context.
        app_ctx = _app_ctx_stack.top
        if app_ctx is None or app_ctx.app != self.app:
            app_ctx = self.app.app_context()
            app_ctx.push()
            self._implicit_app_ctx_stack.append(app_ctx)
        else:
            self._implicit_app_ctx_stack.append(None)

        _request_ctx_stack.push(self)
#         logg.debug("pushed RequestContext %s", self)

    def pop(self, exc=None):
        app_ctx = self._implicit_app_ctx_stack.pop()
        rv = _request_ctx_stack.pop()
        assert rv is self, 'Popped wrong request context.  (%r instead of %r)' \
            % (rv, self)
#         logg.debug("popped RequestContext %s", self)
        # Get rid of the app as well if necessary.
        if app_ctx is not None:
            app_ctx.pop(exc)


class AppContext():

    def __init__(self, app):
        self.app = app
        # Like request context, app contexts can be pushed multiple times
        # but there a basic "refcount" is enough to track them.
        self._refcnt = 0
        self.g = app.app_ctx_globals_class()

    def push(self):
        """Binds the app context to the current context."""
        self._refcnt += 1
        _app_ctx_stack.push(self)
#         logg.debug("pushed AppContext %s", self)

    def pop(self, exc=None):
        """Pops the app context."""
        self._refcnt -= 1
        rv = _app_ctx_stack.pop()
        assert rv is self, 'Popped wrong app context.  (%r instead of %r)' \
            % (rv, self)
#         logg.debug("popped AppContext %s", self)
