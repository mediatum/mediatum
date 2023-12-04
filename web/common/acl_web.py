# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from itertools import imap as map
from itertools import ifilter as filter
range = xrange

import functools as _functools
import itertools as _itertools

import sqlalchemy.orm.exc as _sqlalchemy_orm_exc

import core.translation as _core_translation
from core.database.postgres.permission import AccessRuleset
from core import db
import utils.utils as _utils_utils

q = db.query


def make_acl_html_options(node, ruletype, language):
    rights = []
    with _utils_utils.suppress(_sqlalchemy_orm_exc.DetachedInstanceError, warn=False):
        rights.extend(r.ruleset_name for r in node.access_ruleset_assocs.filter_by(ruletype=ruletype))
    rights = list(filter(None, rights))

    # ignore private rulesets starting with _
    rulelist = q(AccessRuleset).filter(~AccessRuleset.name.like("\_%")).order_by(AccessRuleset.name).all()

    left = []
    right = []

    # node-level standard rules
    for rule in rulelist:
        if rule.name in rights:
            left.append((rule.name, rule.description))
            rights.remove(rule.name)
        else:
            right.append((rule.name, rule.description))

    # node-level implicit rules
    for right in rights:
        # special rights starting with "{" not changeable in normal ACL area
        left.append((
            right,
            _core_translation.translate(language, "edit_acl_special_rule") if right.startswith("{") else right,
           ))

    esc_map = _functools.partial(map, _functools.partial(_utils_utils.esc))
    return dict(
        left="\n".join(_itertools.starmap("<option value=\"{}\">{}</option>".format, map(esc_map, left))),
        right="\n".join(_itertools.starmap("<option value=\"{}\">{}</option>".format, map(esc_map, right))),
       )
