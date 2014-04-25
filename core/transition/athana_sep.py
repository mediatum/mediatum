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
from __future__ import absolute_import, print_function

# athana_http = athana_server = None

try:
    from core import athana_http
    print("athana_http imported (separated athana)")
    from core import athanaserver
    print("athanaserver imported (separated athana)")
except ImportError:
    from core import athana as athanaserver
    athana_http = athanaserver
    print("athana imported (monolithic athana)")
