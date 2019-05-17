# -*- coding: utf-8 -*-

from __future__ import division, absolute_import, print_function

import os
import flask as _flask
from jinja2.loaders import BaseLoader, FileSystemLoader
from jinja2.environment import Environment as BaseEnvironment
from jinja2.exceptions import TemplateNotFound
from pyjade.ext.jinja import Compiler as JinjaCompiler
from pyjade.ext.jinja import PyJadeExtension as JinjaJadeExtension
from pyjade.utils import process
from utils.compat import itervalues
from utils.utils import suppress

class JinjaAutoescapeCompiler(JinjaCompiler):
    autocloseCode = 'if,for,block,filter,autoescape,with,trans,spaceless,comment,cache,macro,localize,compress,call'.split(',')

    def visitCode(self, code):
        if code.buffer:
            val = code.val.lstrip()
            val = self.var_processor(val)
            self.buf.append('%s%s%s' % (self.variable_start_string, val,
                                        self.variable_end_string))
        else:
            self.buf.append('{%% %s %%}' % code.val)

        if code.block:
            self.visit(code.block)
            if not code.buffer:
                codeTag = code.val.strip().split(' ', 1)[0]
                if codeTag in self.autocloseCode:
                    self.buf.append('{%% end%s %%}' % codeTag)


class PyJadeExtension(JinjaJadeExtension):

    def preprocess(self, source, name, filename=None):
        if (not name or
                (name and not os.path.splitext(name)[1] in self.file_extensions)):
            return source
        return process(source, filename=name, compiler=JinjaAutoescapeCompiler, **self.options)


class DispatchingJinjaLoader(BaseLoader):

    """A loader that looks for templates in the application and all
    the blueprint folders.
    """

    def __init__(self, app):
        self.app = app

    def get_source(self, environment, template):
        for loader, local_name in self._iter_loaders(template):
            with suppress(TemplateNotFound, warn=False):
                return loader.get_source(environment, local_name)

        raise TemplateNotFound(template)

    def _iter_loaders(self, template):
        """changes from flask:
        * removed old module blueprints
        * changed order to load templates from blueprints first (so plugins can 'overwrite' templates)
        """
        for blueprint in itervalues(self.app.blueprints):
            loader = blueprint.jinja_loader
            if loader is not None:
                yield loader, template

        loader = self.app.jinja_loader
        if loader is not None:
            yield loader, template


class Environment(BaseEnvironment):

    """Works like a regular Jinja2 environment but has some additional
    knowledge of how blueprint works so that it can prepend the
    name of the blueprint to referenced templates if necessary.
    """

    def __init__(self, app, **options):
        if 'loader' not in options:
            options['loader'] = DispatchingJinjaLoader(app)
        BaseEnvironment.__init__(self, **options)
        self.app = app


def make_template_functions(template_dirpath, global_names={}):
    """Creates a template rendering function which uses a fixed template path
    :param global_names: names to add to all template contexts. Use this to add functions that should be avaiable in all templates.
    """
    jinja_env = Environment(_flask.globals.current_app, loader=FileSystemLoader(template_dirpath), extensions=[PyJadeExtension, "jinja2.ext.autoescape"])
    jinja_env.globals.update(global_names)

    def render_template(template, **kwargs):
        template = jinja_env.get_template(template)
        return template.render(**kwargs)

    def render_macro(template, macro_name, **kwargs):
        macro = getattr(jinja_env.get_template(template).module, macro_name)
        return macro(**kwargs)

    return render_template, render_macro
