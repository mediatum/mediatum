# -*- coding: utf-8 -*-

# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division, absolute_import, print_function
from core import Node
from core.postgres import check_type_arg


# root and its children

@check_type_arg
class Root(Node):
    def get_container(self):
        pass

    def get_collection(self):
        pass


@check_type_arg
class Searchmasks(Node):
    pass


@check_type_arg
class Mappings(Node):
    pass


@check_type_arg
class Metadatatypes(Node):
    pass
