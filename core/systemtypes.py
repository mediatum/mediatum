# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""

from __future__ import division, absolute_import, print_function
from core import Node
from core.transition.postgres import check_type_arg


# root and its children

@check_type_arg
class Root(Node):
    pass


@check_type_arg
class Users(Node):
    pass


@check_type_arg
class ExternalUsers(Node):
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


@check_type_arg
class Navigation(Node):
    pass


@check_type_arg
class UserGroups(Node):
    pass


@check_type_arg
class Schedules(Node):
    pass
