# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import core.translation as _core_translation
from core.database.postgres.permission import AccessRuleset
from core import db
from collections import OrderedDict

q = db.query


def makeList(req, name, rights, readonlyrights, overload=0, type=""):
    rightsmap = {}
    rorightsmap = {}
    for r in rights:
        rightsmap[r] = None

    # ignore private rulesets starting with _
    rulelist = q(AccessRuleset).filter(~AccessRuleset.name.like("\_%")).order_by(AccessRuleset.name).all()

    val_left = ""
    val_right = ""

    if not (len(rightsmap) > 0 and overload):
        # inherited standard rules
        for rule in rulelist:
            if rule.name in readonlyrights:
                if rule.description.startswith("{"):
                    val_left += '<optgroup label="{}"></optgroup>'.format(_core_translation.translate(
                            "edit_acl_special_rule",
                            _core_translation.set_language(req.accept_languages),
                        ))
                else:
                    val_left += """<optgroup label="%s"></optgroup>""" % rule.description
                rorightsmap[rule.name] = 1

        # inherited implicit rules
        for rule in readonlyrights:
            if rule not in rorightsmap:
                if rule.startswith("{"):
                    val_left += '<optgroup label="{}"></optgroup>'.format(_core_translation.translate(
                            "edit_acl_special_rule",
                            _core_translation.set_language(req.accept_languages),
                        ))
                else:
                    val_left += """<optgroup label="%s"></optgroup>""" % rule

    # node-level standard rules
    for rule in rulelist:
        if rule.name in rightsmap:
            val_left += """<option value="%s">%s</option>""" % (rule.name, rule.description)
            rightsmap[rule.name] = 1

    # node-level implicit rules
    for r in rightsmap.keys():
        if not rightsmap[r] and r not in rorightsmap:
            if r.startswith("{"):  # special rights not changeable in normal ACL area
                val_left += """<option value="{}">{}</option>""".format(
                        r,
                        translate("edit_acl_special_rule", _core_translation.set_language(req.accept_languages)),
                    )
            else:
                val_left += """<option value="%s">%s</option>""" % (r, r)

    for rule in rulelist:
        if rule.name not in rightsmap and rule.name not in rorightsmap:
            val_right += """<option value="%s">%s</option>""" % (rule.name, rule.description)
    return {"name": name, "val_left": val_left, "val_right": val_right, "type": type}
