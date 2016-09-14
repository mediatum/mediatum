# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2016 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from __future__ import absolute_import
import pytest
from pytest import fixture, yield_fixture
from core.archive import Archive
from core.permission import get_or_add_everybody_rule
from core.database.postgres.permission import AccessRulesetToRule
from core.transition import httpstatus
from web.frontend.filehandlers import fetch_archived, send_image
from utils.testing import make_node_public


def test_fetch_archived(req, session, fake_archive, content_node):
    node = content_node
    node.system_attrs[u"archive_path"] = u"testpath"
    node.system_attrs[u"archive_type"] = u"test"
    session.flush()
    req.path = u"/archive/{}".format(node.id)
    assert fake_archive.get_state(node) == Archive.NOT_PRESENT
    fetch_archived(req)
    assert fake_archive.get_state(node) == Archive.PRESENT


@yield_fixture
def req_for_png_image(session, image_png, req):
    req.request_headers["Accept"] = "image/png"
    session.flush()
    req.path = "/image/" + unicode(image_png.id)
    yield req


@yield_fixture
def req_for_svg_image(session, image_svg, req):
    req.request_headers["Accept"] = "image/svg+xml"
    session.flush()
    req.path = "/image/" + unicode(image_svg.id)
    yield req


@fixture
def public_image_png(image_png):
    image = image_png
    make_node_public(image)
    image._generate_image_formats()
    return image


@pytest.mark.slow
@fixture
def public_image_svg(image_svg):
    image = image_svg
    make_node_public(image)
    image._generate_image_formats()
    return image


def assert_image_file_sent(image, mimetype, request, error=None):
    assert error is None
    image_file = image.files.filter_by(filetype=u"image", mimetype=mimetype).scalar()
    assert image_file, u"error in fixture, image file not present: " + mimetype
    assert (image_file.abspath, mimetype) in request.sent_files_with_mimetype


def test_send_image_accept_anything(public_image_png, req_for_png_image):
    image = public_image_png
    req = req_for_png_image
    req.request_headers["Accept"] = "*/*"
    error = send_image(req)
    assert_image_file_sent(image, u"image/png", req, error)


def test_send_image_png(public_image_png, req_for_png_image):
    image = public_image_png
    req = req_for_png_image
    error = send_image(req)
    assert_image_file_sent(image, u"image/png", req, error)


def test_send_image_png_nothing_preferred_by_client(public_image_png, req_for_png_image):
    image = public_image_png
    req = req_for_png_image
    del req.request_headers["Accept"]
    error = send_image(req)
    assert_image_file_sent(image, u"image/png", req, error)


def test_send_image_extension_png(public_image_png, req_for_png_image):
    image = public_image_png
    req = req_for_png_image
    req.path = "/image/" + unicode(image.id) + ".png"
    error = send_image(req)
    assert_image_file_sent(image, u"image/png", req, error)


@pytest.mark.slow
def test_send_image_svg(public_image_svg, req_for_svg_image):
    image = public_image_svg
    req = req_for_svg_image
    error = send_image(req)
    assert_image_file_sent(image, u"image/svg+xml", req, error)


@pytest.mark.slow
def test_send_image_svg_client_anything(public_image_svg, req_for_svg_image):
    image = public_image_svg
    req = req_for_svg_image
    # client accepts everything, Chrome does this, for example
    req.request_headers["Accept"] = "*/*"
    error = send_image(req)
    assert_image_file_sent(image, u"image/png", req, error)


@pytest.mark.slow
def test_send_image_svg_client_anything_server_prefers_png(public_image_svg, req_for_svg_image):
    image = public_image_svg
    req = req_for_svg_image
    req.request_headers["Accept"] = "*/*"
    image.system_attrs["preferred_mimetype"] = u"image/png"
    error = send_image(req)
    assert_image_file_sent(image, u"image/png", req, error)


@pytest.mark.slow
def test_send_image_svg_server_prefers_png(public_image_svg, req_for_svg_image):
    image = public_image_svg
    req = req_for_svg_image
    image.system_attrs["preferred_mimetype"] = u"image/png"
    error = send_image(req)
    # client wants svg, client gets svg, regardless of server's preferred_mimetype setting
    assert_image_file_sent(image, u"image/svg+xml", req, error)


### failure cases

def test_send_image_no_data_access(req_for_png_image):
    req = req_for_png_image
    error = send_image(req)
    assert error == 404


def test_send_image_no_file(image_png, req_for_png_image):
    req = req_for_png_image
    node = image_png
    error = send_image(req)
    make_node_public(node)
    assert error == 404


def test_send_image_accept_wrong(public_image_png, req_for_png_image):
    req = req_for_png_image
    req.request_headers["Accept"] = "animal/lizard"
    error = send_image(req)
    assert error == httpstatus.HTTP_NOT_ACCEPTABLE


def test_send_image_path_wrong(req_for_png_image):
    req = req_for_png_image
    req.path = "/lizard/"
    error = send_image(req)
    assert error == httpstatus.HTTP_BAD_REQUEST


def test_send_image_extension_wrong(public_image_png, req_for_png_image):
    node = public_image_png
    req = req_for_png_image
    req.path = "/image/" + unicode(node.id) + ".cow"
    error = send_image(req)
    assert error == httpstatus.HTTP_NOT_ACCEPTABLE
