# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2016 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from __future__ import absolute_import
from munch import Munch


def make_files_munch(node):
    d = {}
    for f in node.files:
        existing = d.get(f.filetype)
        if not existing:
            d[f.filetype] = f
        elif isinstance(existing, dict):
            existing[f.mimetype] = f
        else:
            d[f.filetype] = {f2.mimetype: f2 for f2 in [existing, f]}

    return Munch(d)


def make_node_public(node, ruletype=u"all"):
    """
    Sets public rights (the "everybody" rule) for a node for the given `ruletype` or all ruletypes. 
    """
    from core import AccessRulesetToRule
    from core.permission import get_or_add_everybody_rule
    er = get_or_add_everybody_rule()

    def _add(ruletype):
        special_ruleset = node.get_or_add_special_access_ruleset(ruletype)
        rsa = AccessRulesetToRule(rule=er)
        special_ruleset.rule_assocs.append(rsa)

    if ruletype == "all":
        for ruletype in (u"read", u"write", u"data"):
            _add(ruletype)
    else:
        _add(ruletype)


def append_chain_of_containers(length, head, node_factory=None):
    """Uses the `head` node as start node and appends a chain of container children with `length`.
    Like: head -> generated_node_1 -> ... -> generated_node_<length>

    Returns a list of nodes, starting with `head` and containing the generated nodes.
    """
    if node_factory is None:
        from core.test.factories import DirectoryFactory
        node_factory = DirectoryFactory

    node = head
    nodes = [head]
    
    for _ in xrange(length):
        node, prev_node = node_factory(), node
        prev_node.container_children.append(node)
        nodes.append(node)
    
    return nodes


def test_setup():
    """Call this in `conftest.py` before running unit tests.
    Is used by the mediaTUM core unit tests and can be used by plugin `conftest.py` modules.
    """
    import logging
    import os
    import warnings
    from pytest import skip
    from utils.log import TraceLogger

    TraceLogger.skip_trace_lines += ("pytest", )
    # TraceLogger.stop_trace_at = tuple()


    def pytest_addoption(parser):
        parser.addoption('--slow', action='store_true', default=False,
                         help='Also run slow tests')


    def pytest_runtest_setup(item):
        """Skip tests if they are marked as slow and --slow is not given"""
        if getattr(item.obj, 'slow', None) and not item.config.getvalue('slow'):
            skip('slow tests not requested')


    from core import config
    from core.init import add_ustr_builtin, init_db_connector, load_system_types, load_types, connect_db, _set_current_init_state, init_app,\
        check_imports


    # we are doing a 'basic_init()' here for testing that's a bit different from core.init_basic_init()
    # maybe this can be converted to a new init state or replaced by basic_init()

    config.initialize(config_filepath=os.path.join(config.basedir, "test_mediatum.cfg"))   # TODO: test_mediatum.cfg" should be renamed to mediatum_tests.cfg to make it appear besides the usual one
    add_ustr_builtin()
    import utils.log
    utils.log.initialize()
    check_imports()
    init_app()
    init_db_connector()
    load_system_types()
    load_types()
    connect_db()
    from core import db
    db.disable_session_for_test()
    warnings.simplefilter("always")
    _set_current_init_state("basic")

    # Disable setting the user and ip for each version. This leads to some failures in tests and we don't need it there anyways.
    # Versioning tests can enable this later.
    db.athana_continuum_plugin.disabled = True
