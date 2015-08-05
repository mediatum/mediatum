# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""

import logging
import os.path
from pytest import fixture, yield_fixture
from flask import Flask, Response
from wsgi_intercept import requests_intercept, add_wsgi_intercept
import nap.url

logging.basicConfig(level=logging.DEBUG)

HOST = "localhost"
PORT = 8080

STATIC_DIR = os.path.dirname(__file__) + "/test_data"

@fixture
def cl():
    return nap.url.Url("http://{}:{}".format(HOST, PORT))


def add_test_handler(app, func):
    app.add_url_rule("/test", "test", func)
    return app


def add_test_response(app, response_content):
    return add_test_handler(app, lambda: response_content)

def make_app():
    app = Flask("test", static_folder=STATIC_DIR)
    return app

@yield_fixture
def wsgi_intercept_app():
    requests_intercept.install()
    app = make_app()
    add_wsgi_intercept(HOST, PORT, lambda: app)
    yield app
    requests_intercept.uninstall()


@yield_fixture
def athana_app():
    from core.init import add_ustr_builtin
    add_ustr_builtin()
    from core import athana
    athana.threaded_testrun(PORT)
    app = make_app()
    athana.add_wsgi_context("/", app)
    yield app
    athana.stop_testrun()
    # athana uses many global variables, it's best to simply reload it to clean up for the next test...
    reload(athana)


app = athana_app


def test_wsgi_response_text(app, cl):
    add_test_response(app, "text")
    assert cl.get("/test").text == "text"


def test_wsgi_response_multiline(app, cl):
    """athana should not affect line endings"""
    add_test_response(app, u"line1\nline2")
    assert cl.get("/test").text == u"line1\nline2"


def test_wsgi_response_unicode(app, cl):
    add_test_response(app, u"ünicode")
    assert cl.get("/test").text == u"ünicode"


def test_wsgi_response_iterator(app, cl):
    def gen():
        for ii in xrange(5):
            yield str(ii)
    add_test_response(app, Response(gen()))

    assert cl.get("/test").text == u"01234"


def test_wsgi_response_content_type(app, cl):
    add_test_response(app, Response("doesn't matter", mimetype="text/plain"))
    res = cl.get("/test")
    assert res.headers["Content-Type"] == "text/plain; charset=utf-8"


def test_wsgi_response_binary(app, cl):
    res = cl.get("/test_data/test.png")
    assert res.status_code == 200
    with open(os.path.join(STATIC_DIR, "test.png"), "rb") as f:
        assert res.content == f.read()
