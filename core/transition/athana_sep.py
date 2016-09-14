# -*- coding: utf-8 -*-

from __future__ import absolute_import, print_function
import logging

logg = logging.getLogger(__name__)

try:
    from core import athana_http
    logg.debug("athana_http imported (separated athana)")
    from core import athanaserver
    logg.debug("athanaserver imported (separated athana)")
except ImportError:
    from core import athana as athanaserver
    athana_http = athanaserver
    logg.debug("athana imported (monolithic athana)")
