# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from __future__ import division
from __future__ import print_function

import functools as _functools
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
_map_get_item_0 = _functools.partial(_itertools.imap, _operator.itemgetter(0))


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


def getContent(req, ids):
    user = _users.user_from_session()
    hidden_edit_functions_for_current_user = user.hidden_edit_functions

    if 'acls' in hidden_edit_functions_for_current_user:
        req.response.status_code = _httpstatus.HTTP_FORBIDDEN
        return _tal.processTAL({}, file="web/edit/edit.html", macro="access_error", request=req)

    if len(ids) != 1:  # should not happen
        req.response.status_code = _httpstatus.HTTP_FORBIDDEN
        return _tal.processTAL({}, file="web/edit/modules/acls.html", macro="acl_editor_error", request=req)

    idstr, = ids
    node = _core.db.query(_core.Node).get(int(idstr))
    del ids

    # check write access to node
    if not node.has_write_access():
        req.response.status_code = _httpstatus.HTTP_FORBIDDEN
        return _tal.processTAL({}, file="web/edit/edit.html", macro="access_error", request=req)

    if "save" in req.params:
        _log.info("%r change access %r", user, idstr)
        if req.params.get("type") == "acl":

            for rule_type in _rule_types:

                ruleset_names_from_request = req.params.get(u"left{}".format(rule_type))
                ruleset_names_from_request = _split_from_request(ruleset_names_from_request)

                _1, own_ruleset_assocs, _2 = _get_access_rules_info(node, rule_type)

                own_ruleset_names_not_private = _itertools.ifilterfalse(
                        _operator.attrgetter("private"),
                        own_ruleset_assocs,
                      )
                own_ruleset_names_not_private = _itertools.imap(
                        _operator.attrgetter("ruleset_name"),
                        own_ruleset_names_not_private,
                      )
                own_ruleset_names_not_private = frozenset(own_ruleset_names_not_private)

                to_be_removed_rulesets = own_ruleset_names_not_private-ruleset_names_from_request
                to_be_added_rulesets = ruleset_names_from_request-own_ruleset_names_not_private-{'__special_rule__'}

                if to_be_removed_rulesets:
                    _log.info("node %r: %r removing rulesets %r", node, rule_type, to_be_removed_rulesets)
                for ruleset_name in to_be_removed_rulesets:
                    node.access_ruleset_assocs.filter_by(ruleset_name=ruleset_name,
                                                                 ruletype=rule_type).delete()
                if to_be_added_rulesets:
                    _log.info("node %r: %r adding rulesets %r", node, rule_type, to_be_added_rulesets)
                node.access_ruleset_assocs.extend(
                        _db_permission.NodeToAccessRuleset(ruleset_name=rsn, ruletype=rule_type)
                                                                 for rsn in to_be_added_rulesets)

            _core.db.session.commit()

        if req.params.get("type") == "user":

            for rule_type in _rule_types:

                user_ids_from_request = req.params.get(u"leftuser{}".format(rule_type))
                user_ids_from_request = _split_from_request(user_ids_from_request)

                special_ruleset = node.get_special_access_ruleset(rule_type)
                special_rule_assocs = _get_rule_assocs(special_ruleset)

                uids = _itertools.imap(_operator.attrgetter("rule"), special_rule_assocs)
                uids = _itertools.imap(
                        _accessuser_editor_web.decider_is_private_user_group_access_rule,
                        uids,
                      )
                uids = frozenset(u.id for u in uids if isinstance(u, _core.User))

                users_to_add = tuple(_itertools.imap(
                        _core.db.query(_core.User).get,
                        user_ids_from_request-uids,
                      ))
                if users_to_add and not special_ruleset:  # in this case uids_to_remove will be empty
                    special_rule_assocs = node.get_or_add_special_access_ruleset(rule_type).rule_assocs

                special_rule_assocs.extend(
                        _db_permission.AccessRulesetToRule(
                                rule=_get_or_add_private_access_rule_for_user(user),
                                #ruleset=special_ruleset,
                                invert=False,
                                blocking=False,
                              )
                      for user in users_to_add)

                # remove *after* having added users_to_add: a trigger may delete empty rulesets
                for uid in uids-user_ids_from_request:  # this would be `uids_to_remove`

                    user = _core.db.query(_core.User).get(uid)
                    access_rule_id = _get_or_add_private_access_rule_for_user(user).id

                    for rule_assoc in special_rule_assocs:
                        if rule_assoc.rule_id == access_rule_id:
                            _core.db.session.delete(rule_assoc)

                    _core.db.session.flush()


            _core.db.session.commit()

    action = req.params.get("action", "")

    ret = []

    if action in ("get_userlist", ""):

        private_ruleset_names = _core.db.query(_db_permission.NodeToAccessRuleset.ruleset_name)
        private_ruleset_names = private_ruleset_names.filter_by(private=True)
        private_ruleset_names = private_ruleset_names.all()
        private_ruleset_names = _map_get_item_0(private_ruleset_names)
        private_ruleset_names = frozenset(private_ruleset_names)

        rulesetnamelist = _core.db.query(_db_permission.AccessRuleset.name)
        rulesetnamelist = rulesetnamelist.all()
        rulesetnamelist = _map_get_item_0(rulesetnamelist)
        rulesetnamelist = frozenset(rulesetnamelist)
        rulesetnamelist -= private_ruleset_names

        make_context = _acl_editor_web.makeList if not action else _accessuser_editor_web.makeUserList

        for rule_type in _rule_types:
            inherited_ruleset_assocs, own_ruleset_assocs, special_ruleset = _get_access_rules_info(node, rule_type)
            context = make_context(
                    req,
                    own_ruleset_assocs,  # not_inherited_ruleset_names[rule_type],  # rights
                    inherited_ruleset_assocs,  # inherited_ruleset_names[rule_type],  # readonlyrights
                    special_ruleset,  # additional_rules_inherited[rule_type],
                    _get_rule_assocs(special_ruleset),  # additional_rules_not_inherited[rule_type],
                    sorted(rulesetnamelist),
                    tuple(private_ruleset_names),
                    rule_type=rule_type,
                  )
            ret.append(_tal.processTAL(
                    context,
                    file="web/edit/modules/acls.html",
                    macro="edit_acls_selectbox" if not action else "edit_acls_userselectbox",
                    request=req,
                  ))

        if action == 'get_userlist':  # load additional rights by ajax
            req.response.set_data("".join(ret))
            return ""

    runsubmit = ["function runsubmit(){"]
    for rule_type in _rule_types:
        runsubmit.append("\tmark(document.myform.left{});".format(rule_type))
        runsubmit.append("\tmark(document.myform.leftuser{});".format(rule_type))
    runsubmit.append("\tdocument.myform.submit();")
    runsubmit.append("}")

    context = dict(
            runsubmit="\n{}\n".format("\n".join(runsubmit)),
            srcnodeid=req.values.get("srcnodeid", ""),
            idstr=idstr,
            contentacl="".join(ret),
            adminuser=user.is_admin,
            csrf=req.csrf_token.current_token,
          )
    return _tal.processTAL(
            context,
            file="web/edit/modules/acls.html",
            macro="edit_acls",
            request=req,
          )
