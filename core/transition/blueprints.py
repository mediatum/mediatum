# -*- coding: utf-8 -*-

from __future__ import division, absolute_import, print_function
import inspect
import logging
from os import path
from functools import wraps
from jinja2.loaders import FileSystemLoader
from core.transition.helpers import get_root_path, runswith, Response
from core.transition import httpstatus
from core.transition.globals import request


logg = logging.getLogger(__name__)


class AthanaBlueprint(object):

    """Map Flask style blueprints to Athana contexts."""

    def __init__(self, name, import_name, template_folder=None):
        self.name = name
        self.root_path = get_root_path(import_name)
        self.import_name = import_name
        self.template_folder = template_folder
        self.runswith = runswith
        if runswith == "flask":
            self.flask_blueprint = None
        else:
            self.athana_files = {}
            self.athana_context = None

    def _athana_route(self, route):
        def view_decorator_athana(view):
            @wraps(view)
            def _view_decorating_func_athana(req=None):
                wrapped_view = view
                result = view()
                if isinstance(result, Response):
                    if result.response is not None:
                        request.write(result.response)
                    return result.status
                if isinstance(result, int):
                    return result
                else:
                    request.write(result)
                    return httpstatus.HTTP_OK

            # register athana handler
            filepath = path.abspath(inspect.getfile(view))
            ctx = self.athana_context
            # path relative to context root
            relfilepath = path.relpath(filepath, ctx.root)
            athana_file = self.athana_files.get(filepath)
            if athana_file is None:
                athana_file = ctx.addFile(relfilepath, view.__module__)
                self.athana_files[filepath] = athana_file
            # check if we already defined that handler
            maybe_athana_handler = [h for h in athana_file.handlers if h.function == view.func_name]
            if len(maybe_athana_handler) == 1:
                athana_handler = maybe_athana_handler[0]
            elif not maybe_athana_handler:
                athana_handler = athana_file.addHandler(_view_decorating_func_athana)
            else:
                raise Exception("multiple handlers for one function name found!")
            athana_handler.addPattern(route)
            logg.info("added athana route '%s' -> %s/%s", route, relfilepath, view.func_name)
            return _view_decorating_func_athana

        return view_decorator_athana

    def _flask_route(self, route):
        raise NotImplemented("flask support not implemented!")

    def route(self, athana_route=None, flask_route=None):
        """decorator for views which work with Athana and Flask
        TODO: flask part
        """
        if runswith == "flask":
            return self._flask_route(flask_route)
        else:
            return self._athana_route(athana_route)

    @property
    def jinja_loader(self):
        if self.template_folder is not None:
            return FileSystemLoader(path.join(self.root_path, self.template_folder))
