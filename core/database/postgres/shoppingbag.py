# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from sqlalchemy import Table
from .node import Node
from .user import User
from core.shoppingbag import ShoppingBagMixin
from core.database.postgres import db_metadata, integer_fk, rel
from sqlalchemy.orm.collections import attribute_mapped_collection
from core.transition.postgres import check_type_arg


@check_type_arg
class ShoppingBag(Node, ShoppingBagMixin):
    pass


shoppingbag_to_user = Table("shoppingbag_to_user", db_metadata,
                            integer_fk("user.id", name="user_id"),
                            integer_fk("node.id", name="shoppingbag_id")
                            )


User.shoppingbags = rel(ShoppingBag, secondary=shoppingbag_to_user, collection_class=attribute_mapped_collection("name"), backref="users")
