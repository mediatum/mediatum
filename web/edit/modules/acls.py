# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""

import itertools as _itertools
import logging as _logging
import operator as _operator

import mediatumtal.tal as _tal

import core as _core
import core.database.postgres.permission as _db_permission
import core.httpstatus as _httpstatus
import core.permission as _permission
import core.users as _users
import utils.utils as _utils
import web.common.accessuser_editor_web as _accessuser_editor_web
import web.common.acl_editor_web as _acl_editor_web


_rule_types = ("read", "write", "data")

_log = _logging.getLogger(__name__)

_assoc_filter_key = _operator.attrgetter(*"rule invert blocking".split())


def getInformation():
    return dict(version="1.0", system=0)


def _assoc_filter(assocs, to_remove):
    """
    Return those rules in `assocs` that
    do not match any rule in `to_remove`.
    Rules are compared by their attributes
    `rule`, `invert` and `blocking`.
    """
    to_remove = frozenset(_itertools.imap(_assoc_filter_key, to_remove))
    return tuple(a for a in assocs if _assoc_filter_key(a) not in to_remove)

def _get_access_rules_info(node, ruletype):
    own_ruleset_assocs = node.access_ruleset_assocs.filter_by(ruletype=ruletype)
    own_ruleset_assocs = own_ruleset_assocs.all()

    effective_ruleset_assocs = node.effective_access_ruleset_assocs
    effective_ruleset_assocs = effective_ruleset_assocs.filter(
            _db_permission.EffectiveNodeToAccessRuleset.c.ruletype==ruletype)
    effective_ruleset_assocs = effective_ruleset_assocs.all()

    # warn about remaining rule assocs
    remaining_rule_assocs = _assoc_filter(
            node.access_rule_assocs.filter_by(ruletype=ruletype).all(),
            (r
                    for rsa in effective_ruleset_assocs
                    for r in rsa.ruleset.rule_assocs
                  ),
          )
    if remaining_rule_assocs:
        _log.error("node %r: ruletype: %r: REMAINING RULEASSOCS %r (INVALID!)",
                node,
                ruletype,
                tuple(r.to_dict() for r in remaining_rule_assocs),
              )

    return (
            frozenset(effective_ruleset_assocs).difference(own_ruleset_assocs),
            own_ruleset_assocs,
            node.get_special_access_ruleset(ruletype),
          )


def _get_rule_assocs(ruleset):
    return ruleset.rule_assocs if ruleset else []


def _get_or_add_private_access_rule_for_user(user):
    '''
    get the access rule for the private group of this user
    this may be called the private rule for this user
    :param user:
    :return: AccessRule
    '''
    return _permission.get_or_add_access_rule(group_ids=
                                          (user.get_or_add_private_group().id,))

def _split_from_request(param):
    """
    Split param at ";" and return as frozenset.
    Drop all elements that are empty after stripping.
    `None` is allowed and yields an empty result.
    """
    param = (param or u"").split(u";")
    return frozenset(_itertools.ifilter(_operator.methodcaller("strip"), param))


@_utils.dec_entry_log
def getContent(req, ids):
    user = _users.user_from_session()
    hidden_edit_functions_for_current_user = user.hidden_edit_functions

    if 'acls' in hidden_edit_functions_for_current_user:
        req.response.status_code = _httpstatus.HTTP_FORBIDDEN
        return _tal.processTAL({}, file="web/edit/edit.html", macro="access_error", request=req)

    if len(ids) != 1:  # should not happen
        req.response.status_code = _httpstatus.HTTP_FORBIDDEN
        return _tal.processTAL({}, file="web/edit/modules/acls.html", macro="acl_editor_error", request=req)

    # check write access to node
    idstr = ids[0]
    nid = long(idstr)
    node = _core.db.query(_core.Node).get(nid)
    if not node.has_write_access():
        req.response.status_code = _httpstatus.HTTP_FORBIDDEN
        return _tal.processTAL({}, file="web/edit/edit.html", macro="access_error", request=req)

    if "save" in req.params:
        _log.info("%r change access %r", user, idstr)
        if req.params.get("type") == "acl":

            for rule_type in _rule_types:

                ruleset_names_from_request = req.params.get(u"left{}".format(rule_type))
                ruleset_names_from_request = _split_from_request(ruleset_names_from_request)

                inherited_ruleset_assocs, \
                own_ruleset_assocs, \
                special_ruleset = _get_access_rules_info(node, rule_type)

                own_ruleset_names_not_private = [r.ruleset_name for r in own_ruleset_assocs if not r.private]

                to_be_removed_rulesets = set(own_ruleset_names_not_private) - set(ruleset_names_from_request)
                to_be_added_rulesets = set(ruleset_names_from_request) - set(own_ruleset_names_not_private) - {'__special_rule__'}

                if to_be_removed_rulesets:
                    _log.info("node %r: %r removing rulesets %r", node, rule_type, to_be_removed_rulesets)
                    for ruleset_name in to_be_removed_rulesets:
                        node.access_ruleset_assocs.filter_by(ruleset_name=ruleset_name,
                                                             ruletype=rule_type).delete()

                if to_be_added_rulesets:
                    _log.info("node %r: %r adding rulesets %r", node, rule_type, to_be_added_rulesets)
                    for ruleset_name in to_be_added_rulesets:
                        node.access_ruleset_assocs.append(_db_permission.NodeToAccessRuleset(ruleset_name=ruleset_name, ruletype=rule_type))

            _core.db.session.commit()

        if req.params.get("type") == "user":

            for rule_type in _rule_types:

                user_ids_from_request = req.params.get(u"leftuser{}".format(rule_type))
                user_ids_from_request = _split_from_request(user_ids_from_request)

                special_ruleset = node.get_special_access_ruleset(rule_type)
                special_rule_assocs = _get_rule_assocs(special_ruleset)

                special_access_rules = [ra.rule for ra in special_rule_assocs]
                user_test_results = [_accessuser_editor_web.decider_is_private_user_group_access_rule(ar) for ar in special_access_rules]
                uids = [u.id for u in user_test_results if isinstance(u, _core.User)]

                uids_to_remove = list(set(uids) - set(user_ids_from_request))
                uids_to_add = list(set(user_ids_from_request) - set(uids))
                if uids_to_add and not special_ruleset:  # in this case uids_to_remove will be empty
                    special_ruleset = node.get_or_add_special_access_ruleset(rule_type)
                    special_rule_assocs = special_ruleset.rule_assocs

                for uid in uids_to_add:
                    user = _core.db.query(_core.User).get(uid)
                    access_rule = _get_or_add_private_access_rule_for_user(user)
                    rule_assoc = _db_permission.AccessRulesetToRule(rule=access_rule,
                                                     #ruleset=special_ruleset,
                                                     invert=False,
                                                     blocking=False)
                    special_rule_assocs.append(rule_assoc)

                # remove uids_to_remove *after* having added uids_to_add: a trigger may delete empty rulesets
                for uid in uids_to_remove:

                    user = _core.db.query(_core.User).get(uid)
                    access_rule = _get_or_add_private_access_rule_for_user(user)

                    for rule_assoc in special_rule_assocs:
                        if rule_assoc.rule_id == access_rule.id:
                            _core.db.session.delete(rule_assoc)

                    _core.db.session.flush()


            _core.db.session.commit()

    action = req.params.get("action", "")

    retacl = ""
    if not action:

        rulesetnamelist = [t[0] for t in _core.db.query(_db_permission.AccessRuleset.name).order_by(_db_permission.AccessRuleset.name).all()]
        private_ruleset_names = [t[0] for t in _core.db.query(_db_permission.NodeToAccessRuleset.ruleset_name).filter_by(private=True).all()]
        rulesetnamelist = [rulesetname for rulesetname in rulesetnamelist if not rulesetname in private_ruleset_names]

        for rule_type in _rule_types:
            inherited_ruleset_assocs, \
            own_ruleset_assocs, \
            special_ruleset = _get_access_rules_info(node, rule_type)
            retacl += _tal.processTAL(_acl_editor_web.makeList(req,
                                          own_ruleset_assocs,  #not_inherited_ruleset_names[rule_type],  # rights
                                          inherited_ruleset_assocs,  #inherited_ruleset_names[rule_type],  # readonlyrights
                                          special_ruleset,  #additional_rules_inherited[rule_type],
                                          _get_rule_assocs(special_ruleset),  #additional_rules_not_inherited[rule_type],
                                          rulesetnamelist,
                                          private_ruleset_names,
                                          rule_type=rule_type), file="web/edit/modules/acls.html", macro="edit_acls_selectbox", request=req)

    if action == 'get_userlist':  # load additional rights by ajax

        rulesetnamelist = [t[0] for t in _core.db.query(_db_permission.AccessRuleset.name).order_by(_db_permission.AccessRuleset.name).all()]
        private_ruleset_names = [t[0] for t in _core.db.query(_db_permission.NodeToAccessRuleset.ruleset_name).filter_by(private=True).all()]
        rulesetnamelist = [rulesetname for rulesetname in rulesetnamelist if not rulesetname in private_ruleset_names]

        retuser = ""
        for rule_type in _rule_types:
            inherited_ruleset_assocs, \
            own_ruleset_assocs, \
            special_ruleset = _get_access_rules_info(node, rule_type)
            retuser += _tal.processTAL(_accessuser_editor_web.makeUserList(req,
                                               own_ruleset_assocs,  # not_inherited_ruleset_names[rule_type],  # rights
                                               inherited_ruleset_assocs,  # inherited_ruleset_names[rule_type],  # readonlyrights
                                               special_ruleset,  # additional_rules_inherited[rule_type],
                                               _get_rule_assocs(special_ruleset),  # additional_rules_not_inherited[rule_type],
                                               rulesetnamelist,
                                               private_ruleset_names,
                                               rule_type=rule_type), file="web/edit/modules/acls.html", macro="edit_acls_userselectbox", request=req)
        req.response.set_data(retuser)
        return ""

    runsubmit = "\nfunction runsubmit(){\n"
    for rule_type in _rule_types:
        runsubmit += "\tmark(document.myform.left" + rule_type + ");\n"
        runsubmit += "\tmark(document.myform.leftuser" + rule_type + ");\n"
    runsubmit += "\tdocument.myform.submit();\n}\n"

    return _tal.processTAL({"runsubmit": runsubmit, "idstr": idstr, "contentacl": retacl,
                       "adminuser": user.is_admin, "csrf": req.csrf_token.current_token}, file="web/edit/modules/acls.html", macro="edit_acls", request=req)
