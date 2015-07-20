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
    location = os.path.realpath(location)
    containing_dir_path = os.path.realpath(os.path.dirname(os.path.join(config.basedir, location)))
    if containing_dir_path not in sys.path:
        sys.path.append(containing_dir_path)
        logg.info("added to pythonpath: %s", containing_dir_path)

    try:
        m = importlib.import_module(name)
        logg.info("plugin: imported from pythonpath: %s", name)
        return m
    except ImportError:
        logg.error("Exception while loading plugin '%s' from '%s', plugin path '%s'", name, containing_dir_path, location, exc_info=1)
        logg.error("sys path was\n%s", sys.path)
        return None


def init_plugins():
    logg.info("looking for plugins")
    for name, location in config.getsubset("plugins").items():
        logg.info("Initializing plugin named '%s' from '%s'", name, location)
        m = import_plugin_module(name, location.strip(os.sep))
        if m is None:
            logg.warn("couldn't load plugin %s!", name)
        else:
            plugins[name] = m

        # plugins can define an init() method in their package __init__
        if hasattr(m, "init") and callable(m.init):
            m.init()

        # add po file paths
        if hasattr(m, "pofiles"):  
            if len(m.pofiles) > 0:
                logg.info("loading translation files")
                for fp in m.pofiles:
                    translation.addPoFilepath([fp])


def find_plugin_with_theme(theme_name):
    """Look for a plugin which contains the requested theme `theme_name and return its path.`
    :param theme_name: name of the theme (name of theme directory)
    :returns: path to plugin
    """
    for plugin_name, m in iteritems(plugins):
        plugin_path = os.path.dirname(m.__file__)
        logg.info("looking for theme %s in plugin %s", theme_name, plugin_name)
        theme_path = os.path.join(plugin_path, "themes", theme_name)
        if os.path.exists(theme_path):
            return plugin_path
