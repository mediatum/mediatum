# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

from core.translation import translate, lang


def makeList(req, own_ruleset_assocs, inherited_ruleset_assocs, special_ruleset, special_rule_assocs,
             rulesetnamelist, private_ruleset_names, rule_type=''):

    already_shown_left = {}  # ruleset names in left handside lists will not be shown on the right side

    val_left = []
    val_right = []

    # inherited rulesets
    inherited_ruleset_names = [r.ruleset_name for r in inherited_ruleset_assocs]
    for rulesetname in inherited_ruleset_names:
        if rulesetname in private_ruleset_names:
            val_left.append(
                """<optgroup label="%s"></optgroup>""" % (translate("edit_acl_special_rule", lang(req))))
        else:
            val_left.append("""<optgroup label="%s"></optgroup>""" % rulesetname)
            already_shown_left[rulesetname] = 1

    # node level rulesets (not inherited)
    own_ruleset_names = [r.ruleset_name for r in own_ruleset_assocs]
    for rulesetname in own_ruleset_names:
        if rulesetname in private_ruleset_names:
            entry_text = translate("edit_acl_special_rule", lang(req))
            val_left.append(
                """<option value="__special_rule__">%s</optgroup>""" % (entry_text, ))
        else:
            val_left.append("""<option value="%s">%s</option>""" % (rulesetname, rulesetname))
            already_shown_left[rulesetname] = 1

    for rulesetname in rulesetnamelist:
        if rulesetname not in already_shown_left:
            val_right.append("""<option value="%s">%s</option>""" % (rulesetname, rulesetname))

    res = {"name": rule_type, "val_left": "".join(val_left), "val_right": "".join(val_right), "type": rule_type}

    return res
