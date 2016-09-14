# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2016 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from __future__ import absolute_import
from pytest import fixture
from dogpile.cache import make_region
from utils.caching import cache_key_generator_for_node_argument

@fixture
def cached_node_function():
    
    test_cache = make_region(function_key_generator=cache_key_generator_for_node_argument).configure('dogpile.cache.memory')
    
    @test_cache.cache_on_arguments()
    def function_with_node_arg(node):
        return node.id
    
    return function_with_node_arg


@fixture
def cached_node_function_more_args():
    
    test_cache = make_region(function_key_generator=cache_key_generator_for_node_argument).configure('dogpile.cache.memory')
    
    @test_cache.cache_on_arguments()
    def function_with_node_arg_and_more(node, arg1, arg2):
        return node.id, arg1, arg2
    
    return function_with_node_arg_and_more


def test_cache_key_generator_for_node_argument(session, some_node, cached_node_function):
    node = some_node
    res = cached_node_function(node)
    assert res == node.id
    res = cached_node_function(node)
    assert res == node.id


def test_cache_key_generator_for_node_argument_more_args(session, some_node, cached_node_function_more_args):
    args = (some_node, 1, "blah")
    expected = (some_node.id, 1, "blah")
    res = cached_node_function_more_args(*args)
    assert res == expected
    res = cached_node_function_more_args(*args)
    assert res == expected
