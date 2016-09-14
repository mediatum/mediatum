# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2016 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from __future__ import absolute_import
import os
import tempfile

from PIL import Image as PILImage
import pytest
from core import config
from contenttypes.image import _create_zoom_tile_buffer, _create_zoom_archive, get_zoom_zip_filename
from contenttypes.test import fullpath_to_test_image
from contenttypes.test.asserts import assert_thumbnails_ok
from contenttypes.test.helpers import call_event_files_changed
from utils.testing import make_files_munch


def assert_zoom_ok(node):
    zoom_image = node.files.filter_by(filetype=u"zoom").scalar()
    assert zoom_image is not None
    assert zoom_image.size > 1000


def assert_image_formats_ok(image_node):
    mimetype = image_node._test_mimetype
    files = make_files_munch(image_node)

    assert "original" in files
    assert "image" in files

    if mimetype == u"image/tiff":
        assert "image/png" in files.image
        assert "image/tiff" in files.image
        assert files.original.mimetype == "image/tiff"
        assert files.original.path == files.image["image/tiff"].path
        assert files.original.path.replace(".tif", ".png") == files.image["image/png"].path

    elif mimetype == u"image/svg+xml":
        assert "image/svg+xml" in files.image
        assert "image/png" in files.image
        assert files.original.mimetype == "image/svg+xml"
        assert files.original.path == files.image["image/svg+xml"].path
        assert files.original.path.replace(".svg", ".png") == files.image["image/png"].path

    else:
        assert files.original.path == files.image.path
        assert files.original.mimetype == files.image.mimetype


@pytest.mark.slow
def test_image_generate_image_formats(image):
    image._generate_image_formats()
    assert_image_formats_ok(image)


@pytest.mark.slow
def test_image_generate_thumbnails(image):
    image._generate_image_formats()
    image._generate_thumbnails()
    assert_thumbnails_ok(image)


def test_image_create_zoom_tile_buffer(image_png):
    img_path = fullpath_to_test_image("png")
    img = PILImage.open(img_path)
    with _create_zoom_tile_buffer(img, 4, 256, 1, 0, 0) as buff:
        val = buff.getvalue()
        assert val
        tile_img = PILImage.open(buff)
        assert [s for s in tile_img.size if s == 256]


@pytest.mark.slow
def test_create_zoom_archive(image):
    img_path = fullpath_to_test_image("png")
    zip_name = get_zoom_zip_filename(image.id)
    zip_path = os.path.join(config.get('paths.zoomdir'), zip_name)
    _create_zoom_archive(256, img_path, zip_path)
    assert os.stat(zip_path).st_size > 1000


def test_image_extract_metadata(image):
    # for svg, the alternative png format is needed for extraction
    if image._test_mimetype == "image/svg+xml":
        image._generate_image_formats()
    image._extract_metadata()

    # SVG does not support Exif, GIF and PNG are not supported by our ancient exif lib
    if image._test_mimetype in ("image/tiff", "image/jpeg"):
        assert image.get("exif_Image_XResolution") == "300"

@pytest.mark.slow
def test_image_generate_zoom_archive(image):
    image._generate_image_formats()
    image._generate_zoom_archive()
    assert_zoom_ok(image)


def _test_event_files_changed(image):
    with call_event_files_changed(image):
        assert_thumbnails_ok(image)
        assert_image_formats_ok(image)
        if image._test_mimetype != "image/svg+xml":
            assert_zoom_ok(image)

@pytest.mark.slow
def test_event_files_changed_svg(image_svg):
    _test_event_files_changed(image_svg)


@pytest.mark.slow
def test_event_files_changed_png(image_png):
    _test_event_files_changed(image_png)


@pytest.mark.slow
def test_event_files_changed_gif(image_gif):
    _test_event_files_changed(image_gif)


@pytest.mark.slow
def test_event_files_changed_jpeg(image_jpeg):
    _test_event_files_changed(image_jpeg)


@pytest.mark.slow
def test_event_files_changed_tiff(image_tiff):
    _test_event_files_changed(image_tiff)
