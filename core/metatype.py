# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import collections as _collections

import core as _core

EditorHTMLForm = _collections.namedtuple("EditorHTMLForm", "html conflict");


class MetatypeInvalidFormData(Exception):
    def __init__(self, message_id, mapping={}):
        super(Exception, self).__init__(message_id)
        self.message_id = message_id
        self.mapping = mapping

    def get_translated_message(self):
        return _core.translation.translate_in_request(self.message_id, mapping=self.mapping)


class Metatype(object):

    default_settings = None

    def editor_get_html_form(self, metafield, metafield_name_for_html, values, required, language):
        raise AssertionError

    def search_get_html_form(self, context):
        pass

    def viewer_get_data(self, metafield, maskitem, mask, node, language, html):
        pass

    def editor_parse_form_data(self, field, data):
        raise AssertionError

    def get_default_value(self, field):
        return ""

    def admin_settings_get_html_form(self, field, metadatatype, language):
        pass


    def admin_settings_parse_form_data(self, data):
        assert not data
