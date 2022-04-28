# -*- coding: utf-8 -*-

# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
    utils.clients.ui
    ~~~~~~~~~~~~~~~~
    Abstractions for automated mediaTUM web UI access from Python programs.
    Can be used for integration / stress tests or web scraping, for example.
    
    Notice: It's better to use the web API instead in most cases if you want to automate tasks!
"""

from __future__ import division
from __future__ import print_function

from .access import MediatumWebUI, MediatumWebUISession
