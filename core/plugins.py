# -*- coding: utf-8 -*-
"""
 mediatum - a multimedia content repository

 Copyright (C) 2013 Tobias Stenzel <tobias.stenzel@tum.de>

 This program is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.

 This program is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
from __future__ import division

import logging
import importlib
from pprint import pformat
import os.path
import sys

from core import config, translation
from utils.compat import iteritems


logg = logging.getLogger(__name__)


plugins = {}


def import_plugin_module(name, location):
    location = location.rstrip(os.sep)

    if not os.path.isabs(location):
        location = os.path.join(config.basedir, location)

    containing_dir_path = os.path.realpath(os.path.dirname(location))

    if containing_dir_path not in sys.path:
        sys.path.append(containing_dir_path)
        logg.info("added to pythonpath: %s", containing_dir_path)

    try:
        m = importlib.import_module(name)
        return m
    except ImportError:
        logg.exception("Exception while loading plugin '%s' from '%s', plugin path '%s'", name, containing_dir_path, location)
        logg.error("sys path was\n%s", sys.path)
        return None


def init_plugins():
    for name, location in config.getsubset("plugins").items():
        m = import_plugin_module(name, location)
        if m is None:
            logg.warning("couldn't load plugin %s!", name)
        else:
            logg.info("Initializing plugin '%s' from '%s'", name, location or "pythonpath")
            plugins[name] = m

        # plugins can define an init() method in their package __init__
        if hasattr(m, "init") and callable(m.init):
            m.init()

        # add po file paths
        if hasattr(m, "pofiles"):  
            if len(m.pofiles) > 0:
                logg.debug("loading translation files for plugin %s", name)
                for fp in m.pofiles:
                    translation.addPoFilepath([fp])


def find_plugin_with_theme(theme_name):
    """Look for a plugin which contains the requested theme `theme_name and return its path.`
    :param theme_name: name of the theme (name of theme directory)
    :returns: path to plugin
    """
    for plugin_name, m in iteritems(plugins):
        plugin_path = os.path.dirname(m.__file__)
        logg.debug("looking for theme %s in plugin %s", theme_name, plugin_name)
        theme_path = os.path.join(plugin_path, "themes", theme_name)
        if os.path.exists(theme_path):
            return plugin_path


def init_web_routes():
    """
    Call init_web_route for each plugin.
    This allows plugin to add web routes after the flask app object is initialized.
    :return:
    """
    for name, module in plugins.iteritems():
        if hasattr(module, "init_web_route") and callable(module.init_web_route):
            logg.info("Initializing web route for '%s'", name)
            module.init_web_route()


def add_plugin_file_store_paths():
    """
    Call add_file_store_paths for each plugin.
    This allows plugin to add filestore paths after the flask app object is initialized.
    :return:
    """
    for name, module in plugins.iteritems():
        if hasattr(module, "add_file_store_paths") and callable(module.add_file_store_paths):
            logg.info("Adding filestore paths for '%s'", name)
            module.add_file_store_paths()
