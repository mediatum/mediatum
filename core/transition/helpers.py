# -*- coding: utf-8 -*-

from __future__ import division, absolute_import, print_function

import os
import pkgutil
import sys
from werkzeug.utils import get_content_type
from core.transition.globals import current_app

# global athana / flask switch ;)
runswith = "athana"


def get_root_path(import_name):
    """Returns the path to a package or cwd if that cannot be found.  This
    returns the path of a package or the folder that contains a module.

    Not to be confused with the package path returned by :func:`find_package`.

    !taken from flask.helpers
    """
    # Module already imported and has a file attribute.  Use that first.
    mod = sys.modules.get(import_name)
    if mod is not None and hasattr(mod, '__file__'):
        return os.path.dirname(os.path.abspath(mod.__file__))

    # Next attempt: check the loader.
    loader = pkgutil.get_loader(import_name)

    # Loader does not exist or we're referring to an unloaded main module
    # or a main module without path (interactive sessions), go with the
    # current working directory.
    if loader is None or import_name == '__main__':
        return os.getcwd()

    # For .egg, zipimporter does not have get_filename until Python 2.7.
    # Some other loaders might exhibit the same behavior.
    if hasattr(loader, 'get_filename'):
        filepath = loader.get_filename(import_name)
    else:
        # Fall back to imports.
        __import__(import_name)
        filepath = sys.modules[import_name].__file__

    # filepath is import_name.py for a module, or __init__.py for a package.
    return os.path.dirname(os.path.abspath(filepath))


def get_template_attribute(template_name, attribute):
    """Loads a macro (or variable) a template exports. This can be used to
invoke a macro from within Python code. If you for example have a
template named `_cider.html` with the following contents:

.. sourcecode:: html+jinja

{% macro hello(name) %}Hello {{ name }}!{% endmacro %}

You can access this from Python code like this::

hello = get_template_attribute('_cider.html', 'hello')
return hello('World')

.. !taken from flask.helpers

:param template_name: the name of the template
:param attribute: the name of the variable of macro to access
"""
    return getattr(current_app.jinja_env.get_template(template_name).module,
                   attribute)


class Response(object):

    """
    Response hack which looks similar to the Werkzeug response
    """

    def __init__(self, response=None, status=None, headers=None,
                 mimetype=None, content_type=None):
        self.response = response
        self.status = status or 200
        self.headers = headers or []
        self.mimetype = mimetype or "text/html"
        self.content_type = get_content_type(self.mimetype, "utf-8")
