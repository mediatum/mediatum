# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2016 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from core import AccessRule, AccessRuleset, AccessRulesetToRule, db
from web.newadmin.views import BaseAdminView


class AccessRuleView(BaseAdminView):

    can_create = False
    can_delete = False
    can_edit = False
    can_view_details = False

    def __init__(self, session=db.session, *args, **kwargs):
        super(AccessRuleView, self).__init__(AccessRule, session, category="ACL", *args, **kwargs)


class AccessRulesetView(BaseAdminView):

    can_create = False
    can_delete = False
    can_edit = False
    can_view_details = False

    form_colums = ("name", "description")
    column_filters = form_colums
    column_searchable_list = form_colums

    def __init__(self, session=db.session, *args, **kwargs):
        super(AccessRulesetView, self).__init__(AccessRuleset, session, category="ACL", *args, **kwargs)


class AccessRulesetToRuleView(BaseAdminView):

    can_create = False
    can_delete = False
    can_edit = False
    can_view_details = False

    def __init__(self, session=db.session, *args, **kwargs):
        super(AccessRulesetToRuleView, self).__init__(AccessRulesetToRule, session, category="ACL", *args, **kwargs)
