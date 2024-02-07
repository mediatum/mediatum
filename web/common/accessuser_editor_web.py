# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import logging

import core.translation as _core_translation
from core import db
from core.database.postgres.permission import AccessRuleset, AccessRule
from core.database.postgres.user import AuthenticatorInfo
from core.database.postgres.user import User
from core.database.postgres.user import UserGroup
from core.database.postgres.user import UserToUserGroup
from utils import utils as _utils_utils

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
        logg.warning("%s", msg)
        raise ValueError(msg)
    else:
        user = None

    if not user:
        msg = "no user with private group id %r for access rule %r" % (gid, ar.to_dict())
        logg.warning("%s", msg)
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
    language = _core_translation.set_language(req.accept_languages)
    for ai in q(AuthenticatorInfo).all():
        id2user_prefix = u"{}:{}: ".format(ai.auth_type, ai.name)
        with _utils_utils.suppress(_core_translation.MessageIdNotFound, warn=False):
            id2user_prefix = _core_translation.translate(language, id2user_prefix)
        authenticator_id2user_prefix[ai.id] = id2user_prefix
    user_not_inherited_in_left_list = []

    own_ruleset_names = [r.ruleset_name for r in own_ruleset_assocs]
    for ruleset_name in own_ruleset_names:
        if ruleset_name in private_ruleset_names:
            ruleset = q(AccessRuleset).filter_by(name=ruleset_name).scalar()
            for rule_assoc in ruleset.rule_assocs:
                rule = rule_assoc.rule
                test_result = decider_is_private_user_group_access_rule(rule)
                if type(test_result) in [unicode, str]:
                    val_left += u'<option value="" title="{0}">{0}</option>'.format(_utils_utils.esc(test_result))
                elif type(test_result) == User:
                    long_val = get_list_representation_for_user(
                            test_result,
                            prefix=authenticator_id2user_prefix[test_result.authenticator_id],
                        )
                    val_left += u'<option value="{0}" title="{1}">{1}</option>'.format(
                            test_result.id,
                            _utils_utils.esc(long_val),
                        )
                    user_not_inherited_in_left_list.append(test_result.id)
                else:
                    param_value = 'rule_id:%r' % rule.id
                    text_content = "rule: %r" % rule.to_dict()
                    val_left += u'<option value="{0}" title="{1}">{1}</option>'.format(
                            param_value,
                            _utils_utils.esc(text_content),
                        )
        else:
            val_left += u'<option value="" title="{0}">{0}</option>'.format(_utils_utils.esc(ruleset_name))

    inherited_ruleset_names = [r.ruleset_name for r in inherited_ruleset_assocs]
    for ruleset_name in inherited_ruleset_names:
        if ruleset_name in private_ruleset_names:
            ruleset = q(AccessRuleset).filter_by(name=ruleset_name).scalar()
            for rule_assoc in ruleset.rule_assocs:
                rule = rule_assoc.rule
                test_result = decider_is_private_user_group_access_rule(rule)

                if type(test_result) in [unicode, str]:
                    val_left += u'<optgroup label="{0}" title="{0}"/>'.format(_utils_utils.esc(test_result))
                elif type(test_result) == User:
                    long_val = get_list_representation_for_user(
                            test_result,
                            prefix=authenticator_id2user_prefix[test_result.authenticator_id],
                        )
                    val_left += u'<optgroup label="{0}" title="{0}"/>'.format(_utils_utils.esc(long_val))
                else:
                    param_value = 'rule_id:%r' % rule.id
                    text_content = "rule: %r" % rule.to_dict()
                    val_left += u'<option value="{0}" title="{1}">{1}</option>'.format(
                            param_value,
                            _utils_utils.esc(text_content),
                        )
        else:
            val_left += u'<optgroup label="{0}" title="{0}"/>'.format(_utils_utils.esc(ruleset_name))

    sorted_decorated_userlist = sorted([(authenticator_id2user_prefix[u.authenticator_id], u.getName().lower(), u) for u in userlist])
    for u_prefix, u_name, u in sorted_decorated_userlist:
        if u.id in user_not_inherited_in_left_list:
            continue
        long_val = get_list_representation_for_user(u, prefix=u_prefix)
        val_right += u'<option value="{0}" title="{1}">{1}</option>'.format(u.id, _utils_utils.esc(long_val))

    return {"name": rule_type, "val_left": val_left, "val_right": val_right, "type": rule_type}
