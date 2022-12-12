# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

from warnings import warn


class Metatype(object):

    default_settings = None

    def editor_get_html_form(self, field, value="", width=400, lock=0, language=None, required=None):
        return ""

    def search_get_html_form(self, context):
        pass

    def viewer_get_data(self, metafield, maskitem, mask, node, language, html):
        pass

    def editor_parse_form_data(self, field, form):
        """Prepare value for the database from update request params.
        :param field:   associated field
        :param params: dict which contains POST form values
        :param item: field name prepended with language specifier. Is the same as field name for non-multilingual fields.
        """
        # just fetch the unmodified value from the params dict
        return form.get(field.name)

    def get_default_value(self, field):
        return ""

    def admin_settings_get_html_form(self, field, metadatatype, language):
        pass


    def admin_settings_parse_form_data(self, data):
        assert not data
