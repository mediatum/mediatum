# -*- coding: utf-8 -*-
#  this package is part of mediatum - a multimedia content repository
#
#  Copyright (C) 2014 Tobias Stenzel <tobias.stenzel@tum.de>
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
    core.transition
    ~~~~~~~~~~~~~~~
    module to aid the transition from athana HTTP to WSGI / Flask.
    Many parts are taken from or inspired by Flask 0.10.

    :copyright: (C) 2014 by Tobias Stenzel <tobias.stenzel@tum.de>
    :license: GPL 3, see COPYING for more details.
"""

from jinja2 import Markup
from core.transition.app import create_app
from core.transition.blueprints import AthanaBlueprint
from core.transition.globals import request, session, g
from core.transition.templating import render_macro, render_template, render_template_string, make_template_functions
