# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""

from __future__ import division, absolute_import, print_function
from core import Node
from core.transition.postgres import check_type_arg


# root and its children

class Root(Node):
    pass


@check_type_arg
class Users(Node):
    pass

class ExternalUsers(Node):
    pass

class Searchmasks(Node):
    pass


class Mappings(Node):
    pass


class Metadatatypes(Node):
    pass


class Navigation(Node):
    pass


class UserGroups(Node):
    pass
