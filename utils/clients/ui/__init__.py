# -*- coding: utf-8 -*-
#  this package is part of mediatum - a multimedia content repository
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
    utils.clients.ui
    ~~~~~~~~~~~~~~~~
    Abstractions for automated mediaTUM web UI access from Python programs.
    Can be used for integration / stress tests or web scraping, for example.
    
    Notice: It's better to use the web API instead in most cases if you want to automate tasks!

    :copyright: (C) 2015 by the mediaTUM authors
    :license: GPL 3, see COPYING for more details.
"""
from __future__ import division

from .access import MediatumWebUI, MediatumWebUISession
