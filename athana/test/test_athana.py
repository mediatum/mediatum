# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""

import logging
import os.path
from pytest import fixture, yield_fixture
from flask import Flask, Response, request
import nap.url
from core import athana

logging.basicConfig(level=logging.DEBUG)

HOST = "localhost"
PORT = 8080
BASE_URL = "http://{}:{}".format(HOST, PORT)
STATIC_DIR = os.path.dirname(__file__) + "/test_data"


def static_file_path(filename):
    return os.path.join(STATIC_DIR, filename)


@fixture
def cl():
    return nap.url.Url(BASE_URL)


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
    """Creates WSGI app that receives input directly from requests via wsgi_intercept.
    This skips HTTP request to athana and can be used to test the tests"""
    from wsgi_intercept import requests_intercept, add_wsgi_intercept
    requests_intercept.install()
    app = make_app()
    add_wsgi_intercept(HOST, PORT, lambda: app)
    yield app
    requests_intercept.uninstall()


@yield_fixture
def athana_app():
    """Creates WSGI app and starts athana in its own thread to avoid blocking the main thread"""
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


def test_wsgi_redirect(app, cl):
    from flask import redirect
    add_test_response(app, redirect("/to/hell"))
    res = cl.get("/test", allow_redirects=False)
    assert res.status_code == 302
    assert res.headers["Location"] == BASE_URL + "/to/hell"


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


def test_wsgi_exception(app, cl, caplog):
    caplog.setLevel(logging.ERROR)
    def fail():
        raise Exception("epic fail!")
    add_test_handler(app, fail)
    res = cl.get("/test")
    assert res.status_code == 500
    # check if logging reported our stupid exception ;)
    rec = caplog.records()[-1]
    assert rec.exc_info[1].args[0] == "epic fail!"


def test_wsgi_response_binary(app, cl):
    res = cl.get("/test_data/test.png")
    assert res.status_code == 200
    with open(static_file_path("test.png"), "rb") as f:
        assert res.content == f.read()


def test_wsgi_get_query_param(app, cl):
    @app.route("/test")
    def echo_query_param():
        #assert request.args["param"] == "value"
        # we don't want to fail in the server part, just return empty strings on failue
        return request.args.get("param1", "") + request.args.get("param2", "")

    res = cl.get("/test?param1=test&param2=passed")
    assert res.text == "testpassed"


def test_wsgi_get_url_arg(app, cl):

    @app.route("/test/<param1>/<param2>")
    def echo_url_args(param1, param2):
        return param1 + param2

    res = cl.get("/test/test/passed")
    assert res.text == "testpassed"


def test_wsgi_post_form(app, cl):

    @app.route("/test", methods=["POST"])
    def echo_form_data():
        # we don't want to fail in the server part, just return empty strings on failue
        return request.form.get("param1", "") + request.form.get("param2", "")

    form_data = {
        "param1": "test",
        "param2": "passed"
    }

    assert cl.post("/test", data=form_data).text == "testpassed"


def test_wsgi_post_form_unicode(app, cl):

    @app.route("/test", methods=["POST"])
    def echo_form_data():
        # we don't want to fail in the server part, just return empty strings on failue
        return request.form.get("param1", "") + request.form.get("param2", "")

    form_data = {
        "param1": u"test",
        "param2": u"päßed"
    }

    assert cl.post("/test", data=form_data).text == u"testpäßed"


def test_wsgi_text_upload(app, cl):

    @app.route("/test", methods=["POST"])
    def echo_text():
        content = request.files.values()[0].read()
        return Response(content, mimetype="text/plain")

    res = cl.post("/test", files={"file": ("testfile", "testpassed")})
    assert res.content == "testpassed"


def test_wsgi_binary_upload(app, cl):

    @app.route("/test", methods=["POST"])
    def echo_png():
        content = request.files.values()[0].read()
        return Response(content, mimetype="image/png")

    with open(static_file_path("test.png"), "rb") as fi:
        content = fi.read()
        fi.seek(0)
        res = cl.post("/test", files={"file": fi})

    assert res.content == content


def test_build_reply_header_with_unicode():
    req = athana.http_request(*([None] * 6))
    req.reply_headers = {}
    req.reply_headers[u"kä1"] = u"vä"
    req.reply_headers["k1"] = "v"
    req.reply_headers[u"kä2"] = "v"
    req.reply_headers["k2"] = u"vä"
    reply_header = req.build_reply_header()
    assert "kä1: vä" in reply_header
    assert "k1: v" in reply_header
    assert "kä2: v" in reply_header
    assert "k2: vä" in reply_header
    