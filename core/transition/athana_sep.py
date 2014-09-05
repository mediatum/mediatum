# -*- coding: utf-8 -*-


from __future__ import absolute_import, print_function

try:
    from core import athana_http
    print("athana_http imported (separated athana)")
    from core import athanaserver
    print("athanaserver imported (separated athana)")
except ImportError:
    from core import athana as athanaserver
    athana_http = athanaserver
    print("athana imported (monolithic athana)")
