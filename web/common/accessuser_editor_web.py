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
import logging

from core.translation import translate, lang
from core.database.postgres.permission import AccessRuleset, AccessRule
from core import User, AuthenticatorInfo
from core import db, UserToUserGroup, UserGroup

q = db.query
logg = logging.getLogger(__name__)

def decider_is_private_user_group_access_rule(ar):
    """
    :param ar: access rule
    :return: None, if no user can be identified that this rule represents the private user group for
             u"compatibility: pug for formaly dynamic user" if remnant of rule for abandoned dynamic users (old mediatum version)
             user object matching criteria
    """

    if not (ar.group_ids and len(ar.group_ids) == 1):
        return None

    if ar.invert_date or ar.invert_group or ar.invert_subnet:
        return None

    if ar.subnets:
        return None

    gid = ar.group_ids[0]
    if gid:
        usergroup = q(UserGroup).get(gid)
        cand_uids = [t[0] for t in q(UserToUserGroup.user_id).filter_by(usergroup_id=gid).filter_by(private=True).all()]
        if not cand_uids:
            # for mediatums migrated from mysql - may be removed after migration
            if gid >= 99990000:
                return u"compatibility: private usergroup for dynamic user: gid=%r" % gid
            return None
        elif len(cand_uids) == 1:
            uid = cand_uids[0]
            user = q(User).get(uid)
            return user
        else:
            msg = u"data integrity error (?): usergroup %r is 'private' to more than one (%d) user" % (usergroup,
                                                                                                     len(cand_uids))
        logg.warning(msg)
        raise ValueError(msg)
    else:
        user = None

    if not user:
        msg = "no user with private group id %r for access rule %r" % (gid, ar.to_dict())
        logg.warning(msg)
        return msg

    return user


def get_list_representation_for_user(user, prefix=u""):
    u_login_name = user.login_name or u''
    u_display_name = user.display_name or u''
    u_lastname = user.lastname or u''
    u_firstname = user.firstname or u''

    res = u_login_name
    if not res:
        res = u_display_name
    elif u_display_name:
        res = u"%s - %s" % (res, u_display_name)

    if u_lastname and not (u_lastname in res and u_firstname in res):
        res = u"%s (%s, %s)" % (res, u_lastname, u_firstname)

    # do not expose user.comment to non-admins
    #if res == u_login_name and user.comment:
    #    res = u"%s (%s)" % (res, user.comment)

    if prefix:
        res = u"%s%s" % (prefix, res)

    return res


def makeUserList(req, own_ruleset_assocs, inherited_ruleset_assocs, special_ruleset, special_rule_assocs,
             rulesetnamelist, private_ruleset_names, rule_type=''):

    val_left = ""
    val_right = ""
    userlist = q(User).order_by(User.display_name).all()
    authenticator_id2user_prefix = {}
    for ai in q(AuthenticatorInfo).all():
        authenticator_id2user_prefix[ai.id] = translate(u"%s:%s: " % (ai.auth_type, ai.name), lang(req))

    user_not_inherited_in_left_list = []

    own_ruleset_names = [r.ruleset_name for r in own_ruleset_assocs]
    for ruleset_name in own_ruleset_names:
        if ruleset_name in private_ruleset_names:
            ruleset = q(AccessRuleset).filter_by(name=ruleset_name).scalar()
            for rule_assoc in ruleset.rule_assocs:
                rule = rule_assoc.rule
                test_result = decider_is_private_user_group_access_rule(rule)

                if type(test_result) in [unicode, str]:
                    if len(test_result) > 50:
                        val_left += """<option value="" title="%s">%s</option>""" % (test_result, test_result)
                    else:
                        val_left += """<option value="">%s</option>""" % (test_result,)
                elif type(test_result) == User:
                    long_val = get_list_representation_for_user(test_result,
                                                                prefix=authenticator_id2user_prefix[test_result.authenticator_id])
                    if len(long_val) > 50:
                        val_left += """<option value="%s" title="%s">%s</option>""" % (test_result.id, long_val, long_val)
                    else:
                        val_left += """<option value="%s">%s</option>""" % (test_result.id, long_val,)
                    user_not_inherited_in_left_list.append(test_result.id)
                else:
                    param_value = 'rule_id:%r' % rule.id
                    text_content = "rule: %r" % rule.to_dict()
                    val_left += """<option value="%s" title="%s">%s</option>""" % (param_value, text_content, text_content)
        else:
            if len(ruleset_name) > 50:
                val_left += """<option value="" title="%s">%s</option>""" % (ruleset_name, ruleset_name)
            else:
                val_left += """<option>%s</option>""" % (ruleset_name,)

    inherited_ruleset_names = [r.ruleset_name for r in inherited_ruleset_assocs]
    for ruleset_name in inherited_ruleset_names:
        if ruleset_name in private_ruleset_names:
            ruleset = q(AccessRuleset).filter_by(name=ruleset_name).scalar()
            for rule_assoc in ruleset.rule_assocs:
                rule = rule_assoc.rule
                test_result = decider_is_private_user_group_access_rule(rule)

                if type(test_result) in [unicode, str]:
                    if len(test_result) > 50:
                        val_left += """<optgroup label="%s" title="%s"></optgroup>""" % (test_result, test_result)
                    else:
                        val_left += """<optgroup label="%s"></optgroup>""" % (test_result,)
                elif type(test_result) == User:
                    long_val = get_list_representation_for_user(test_result, prefix=authenticator_id2user_prefix[test_result.authenticator_id])
                    if len(long_val) > 50:
                        val_left += """<optgroup label="%s" title="%s"></optgroup>""" % (long_val, long_val)
                    else:
                        val_left += """<optgroup label="%s"></optgroup>""" % (long_val, )
                else:
                    param_value = 'rule_id:%r' % rule.id
                    text_content = "rule: %r" % rule.to_dict()
                    val_left += """<option value="%s" title="%s">%s</option>""" % (
                    param_value, text_content, text_content)
        else:
            if len(ruleset_name) > 50:
                val_left += """<optgroup label="%s" title="%s"></optgroup>""" % (ruleset_name, ruleset_name)
            else:
                val_left += """<optgroup label="%s"></optgroup>""" % (ruleset_name,)

    sorted_decorated_userlist = sorted([(authenticator_id2user_prefix[u.authenticator_id], u.getName().lower(), u) for u in userlist])
    for u_prefix, u_name, u in sorted_decorated_userlist:
        if u.id in user_not_inherited_in_left_list:
            continue
        long_val = get_list_representation_for_user(u, prefix=u_prefix)
        if len(long_val) > 50:
            val_right += """<option value="%s" title="%s">%s</option>""" % (u.id, long_val, long_val)
        else:
            val_right += """<option value="%s">%s</option>""" % (u.id, long_val)

    return {"name": rule_type, "val_left": val_left, "val_right": val_right, "type": rule_type}
