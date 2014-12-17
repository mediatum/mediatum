# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from web.frontend import login
from pytest import fixture


@fixture(autouse=True)
def login_patch(monkeypatch, user, nav_frame):
    import core.users
    import web.frontend.frame
    monkeypatch.setattr(core.users, "getUserFromRequest", lambda req: user)
    monkeypatch.setattr(web.frontend.frame, "getNavigationFrame", lambda req: nav_frame)

### TODO: login POST tests

### TODO: wrong args tests

### Referer tests

def test_login_no_referer(req):
    assert login.login(req) == 200
    assert req.session["return_after_login"] is False 
    
    
def test_login_from_login_page(req):
    req.header.append("Referer: /login")
    assert login.login(req) == 200
    assert req.session["return_after_login"] is False 
    
    
def test_login_login_from_edit(req):
    req.header.append("Referer: /edit/edit_content?id=604993")
    assert login.login(req) == 200
    assert req.session["return_after_login"] == "/edit" 
        
        
def test_login_from_other(req):    
    ref = "http://localhost:8081/justatest"
    req.header.append("Referer: " + ref)
    assert login.login(req) == 200
    assert req.session["return_after_login"] == ref
    