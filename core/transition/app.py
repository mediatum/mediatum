# -*- coding: utf-8 -*-

from __future__ import division, absolute_import, print_function
from functools import partial
from collections import OrderedDict
import logging
from os import path
from jinja2.loaders import FileSystemLoader, ChoiceLoader
from werkzeug.datastructures import ImmutableDict, MultiDict
import pyaml
import yaml
from core.transition.templating import PyJadeExtension, Environment
from core.transition.ctx import _AppCtxGlobals, AppContext, RequestContext
from core.transition.frontendincludes import JavascriptIncludes, CSSIncludes
from core.transition.globals import request, session, g
from core.transition.helpers import runswith
from core.transition.helpers import get_root_path
from utils.date import dt_fromiso
import datetime
from werkzeug.utils import cached_property

logg = logging.getLogger(__name__)

if runswith == "athana":
    from core.transition.athana_sep import athana_http


class AthanaTestRequest(athana_http.http_request):

    def __init__(self, params=None, uri="/", headers=None):
        headers = headers or {}
        if "Accept" not in headers:
            headers["Accept"] = "*/*"

        super(AthanaTestRequest, self).__init__(None, None, None, uri, 0, headers)
        self.request_headers = self.headers = headers
        self.params = params or {}
        self.ip = "127.0.0.1"
        self.session = {}
        self.params = {}
        self.form = MultiDict()
        self.args = MultiDict()
        self.path = "/"
        self.request = {}
        self.sent_files_with_mimetype = []

    def get_header(self, header):
        return self.headers.get(header.capitalize())

    def sendFile(self, filepath, mimetype):
        if not path.exists(filepath):
            raise ValueError("cannot send, file not found: " + filepath)
        self.sent_files_with_mimetype.append((filepath, mimetype))

    @property
    def text(self):
        return "\n".join(p.data for p in self.outgoing)


class AthanaFlaskStyleApp(object):

    """Flask style app based on Athana HTTP"""
    #: Options that are passed directly to the Jinja2 environment.
    jinja_options = ImmutableDict(
        extensions=['jinja2.ext.autoescape', 'jinja2.ext.with_', PyJadeExtension]
    )

    app_ctx_globals_class = _AppCtxGlobals

    def __init__(self, import_name, template_folder="web/templates", name="mediatum", **config):
        if "DEBUG" not in config:
            config["DEBUG"] = True
        self.blueprints = {}
        self.name = name
        self.config = config.copy()
        self.extensions = {}
        self.template_folder = template_folder
        self.jinja_env = self.create_jinja_environment()
        self.import_name = import_name
        self.root_path = get_root_path(import_name)
        #: A dictionary with list of functions that are called without argument
        #: to populate the template context.  The key of the dictionary is the
        #: name of the blueprint this function is active for, `None` for all
        #: requests.  Each returns a dictionary that the template context is
        #: updated with.  To register a function here, use the
        #: :meth:`context_processor` decorator.
        self.template_context_processors = {
            None: []
        }

        #: all the attached blueprints in a dictionary by name.  Blueprints

    @property
    def in_development_mode(self):
        return self.config["DEBUG"]

    def register_blueprint(self, blueprint):
        self.blueprints[blueprint.name] = blueprint
        logg.info("added blueprint %s, import name %s", blueprint.name, blueprint.import_name)
        blueprint_reldir = path.relpath(blueprint.root_path, start=athana_http.getBase())
        context_name = blueprint.name if blueprint.name.startswith("/") else "/" + blueprint.name
        ctx = athana_http.addContext(context_name, blueprint_reldir)
        logg.info("added athana context from blueprint with context_name %s, dir %s", context_name, blueprint_reldir)
        blueprint.athana_context = ctx

    def register_with_athana(self):
        from core.transition.athana_sep import athana_http
#         if athana_http.app is not None:
#             raise Exception("App already registered!")
        athana_http.app = self

    def app_context(self):
        return AppContext(self)

    def request_context(self, request, session):
        return RequestContext(self, request, session)

    def context_processor(self, f):
        """Registers a template context processor function."""
        self.template_context_processors[None].append(f)
        return f

    def update_template_context(self, context):
        """Update the template context with some commonly used variables.
        This injects request, session, config and g into the template
        context as well as everything template context processors want
        to inject.  Note that the as of Flask 0.6, the original values
        in the context will not be overridden if a context processor
        decides to return a value with the same key.

        :param context: the context as a dictionary that is updated in place
                        to add extra variables.
        """
        funcs = self.template_context_processors[None]
#         reqctx = _request_ctx_stack.top
#         if reqctx is not None:
#             bp = reqctx.request.blueprint
#             if bp is not None and bp in self.template_context_processors:
#                 funcs = chain(funcs, self.template_context_processors[bp])
        orig_ctx = context.copy()
        for func in funcs:
            context.update(func())
        # make sure the original values win.  This makes it possible to
        # easier add new variables in context processors without breaking
        # existing views.
        context.update(orig_ctx)

    def route(self, route):
        # TODO: todo (see Blueprint)
        pass

    def test_request_context(self):
        """
        TODO: only Athana, should return a flask or athana request and session
        """
#         from core.transition.athana_sep import athana_http

        def data(self):
            return [p.data for p in self.outgoing]
        request = AthanaTestRequest()
        request.session = session = athana_http.Session(1)
        return RequestContext(self, request, session)

    def select_jinja_autoescape(self, filename):
        """Returns `True` if autoescaping should be active for the given
        template name.

        !taken from Flask.
        """
        if filename is None:
            return False
        return filename.endswith(('.html', '.htm', '.xml', '.xhtml'))

    def create_jinja_environment(self):
        """
        !taken from Flask.
        """
        options = dict(self.jinja_options)
        if 'autoescape' not in options:
            options['autoescape'] = self.select_jinja_autoescape
        rv = Environment(self, **options)
        rv.globals.update(
            config=self.config,
            request=request,
            session=session,
            javascript=JavascriptIncludes(self.in_development_mode),
            css=CSSIncludes(self.in_development_mode),
            base_uri="",
            g=g
        )
        rv.filters['yaml'] = yaml.dump
        rv.filters['yaml_safe'] = yaml.safe_dump
        rv.filters['yaml_pretty'] = pyaml.dump
        rv.filters['u'] = partial(unicode, encoding="utf8")
        rv.filters['ordereddict'] = OrderedDict
        rv.filters["dt_fromiso"] = dt_fromiso
        rv.filters["strptime"] = datetime.datetime.strptime
        rv.filters["strftime"] = datetime.datetime.strftime
        #rv.trim_blocks = True
        return rv

    @cached_property
    def jinja_loader(self):
        if self.template_folder is not None:
            loaders = [FileSystemLoader(path.join(self.root_path, self.template_folder))]
        else:
            loaders = []
    
        return ChoiceLoader(loaders)

    def add_template_loader(self, loader, pos=None):
        if pos:
            self.jinja_loader.loaders.insert(pos, loader)
        else:
            self.jinja_loader.loaders.append(loader)
            
    def add_template_globals(self, **global_names):
        self.jinja_env.globals.update(global_names)


def detect_athana_or_flask():
    try:
        from flask import current_app
        if current_app:
            return "flask"
    except:
        pass
    return "athana"


def create_app(name="mediatum"):
    from core import translation
    app = AthanaFlaskStyleApp(name)
    # bind app to athana server
    app.register_with_athana()
    from mediatumbabel import Babel
    babel = Babel(app)
    babel.localeselector(lambda: translation.lang(request))
    return app
