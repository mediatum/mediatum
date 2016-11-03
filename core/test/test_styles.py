# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2016 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from pytest import raises
from core import webconfig
import os
from core import app
from jinja2.exceptions import TemplateNotFound


def test_default_theme_dir():
    webconfig.init_theme()
    jinja_loader = webconfig.theme.make_jinja_loader()
    dirpath = jinja_loader.searchpath[0]
    assert os.path.isdir(dirpath)
    assert dirpath.endswith("templates")


def test_default_theme_render_template_jade():
    webconfig.init_theme()
    ctx = {"ctx_variable": "testvalue"}
    with app.test_request_context():
        html = webconfig.theme.render_template("test.j2.jade", ctx)
    assert "<html>" in html
    assert "testvalue" in html
    

def test_default_theme_render_macro_jade():
    webconfig.init_theme()
    ctx = {"macro_arg": "testvalue"}
    with app.test_request_context():
        html = webconfig.theme.render_macro("test.j2.jade", "testmacro", ctx)
    assert "macro_arg: testvalue" in html
    assert "macro_kwarg: default" in html
    

def test_default_theme_render_macro_kwarg_jade():
    webconfig.init_theme()
    ctx = {"macro_arg": "", "macro_kwarg": "kwargvalue"}
    with app.test_request_context():
        html = webconfig.theme.render_macro("test.j2.jade", "testmacro", ctx)
    assert "macro_kwarg: kwargvalue" in html
    

def test_default_theme_render_template_jade_without_extension_fail():
    webconfig.init_theme()
    ctx = {}
    with raises(TemplateNotFound) as excinfo:
        with app.test_request_context():
            webconfig.theme.render_template("test", ctx)
            
    assert "invalid" in excinfo.value.message
    

def test_default_theme_render_macro_jade_without_extension_fail():
    webconfig.init_theme()
    ctx = {}
    with raises(TemplateNotFound) as excinfo:
        with app.test_request_context():
            webconfig.theme.render_macro("test", "testmacro", ctx)
            
    assert "invalid" in excinfo.value.message
    