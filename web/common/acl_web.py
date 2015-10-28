"""
 mediatum - a multimedia content repository

 Copyright (C) 2007 Arne Seifert <seiferta@in.tum.de>
 Copyright (C) 2007 Matthias Kramm <kramm@in.tum.de>

 This program is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.

 This program is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
from core.translation import translate, lang
from core.database.postgres.permission import AccessRuleset
from core import db

q = db.query


def makeList(req, name, rights, readonlyrights, overload=0, type=""):
    rightsmap = {}
    rorightsmap = {}
    for r in rights:
        rightsmap[r] = None

    rulelist = q(AccessRuleset).all()

    val_left = ""
    val_right = ""

    if not (len(rightsmap) > 0 and overload):
        # inherited standard rules
        for rule in rulelist:
            if rule.name in readonlyrights:
                if rule.description.startswith("{"):
                    val_left += """<optgroup label="%s"></optgroup>""" % (translate("edit_acl_special_rule", lang(req)))
                else:
                    val_left += """<optgroup label="%s"></optgroup>""" % rule.description
                rorightsmap[rule.name] = 1

        # inherited implicit rules
        for rule in readonlyrights:
            if rule not in rorightsmap:
                if rule.startswith("{"):
                    val_left += """<optgroup label="%s"></optgroup>""" % (translate("edit_acl_special_rule", lang(req)))
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
                val_left += """<option value="%s">%s</option>""" % (r, translate("edit_acl_special_rule", lang(req)))
            else:
                val_left += """<option value="%s">%s</option>""" % (r, r)

    for rule in rulelist:
        if rule.name not in rightsmap and rule.name not in rorightsmap:
            val_right += """<option value="%s">%s</option>""" % (rule.name, rule.description)
    return {"name": name, "val_left": val_left, "val_right": val_right, "type": type}
