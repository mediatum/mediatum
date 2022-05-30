# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import logging
import re
from mediatumtal import tal
import utils.date as date
from utils.utils import suppress
from utils.date import format_date, parse_date, validateDate
from core.metatype import Metatype
from schema.schema import dateoption


logg = logging.getLogger(__name__)


class m_date(Metatype):

    name = "date"

    default_settings = dict(
        format=dateoption[0].shortname,
    )

    def editor_get_html_form(self, field, value="", width=400, lock=0, language=None, required=None):
        date_format = field.metatype_data['format']
        d = field.getSystemFormat(date_format)

        if value == "?":
            value = date.format_date(date.now(), d.value)
        with suppress(Exception, warn=False):
            value = date.format_date(date.parse_date(value), d.value)
        return tal.getTAL(
                "metadata/date.html",
                dict(
                    lock=lock,
                    value=value,
                    width=width,
                    name=field.getName(),
                    date_format=date_format,
                    pattern={date.shortname: date.validation_regex
                                 for date in dateoption}[date_format],
                    title=date_format,
                    placeholder=date_format,
                    required=1 if required else None,
                   ),
                macro="editorfield",
                language=language,
               )

    def search_get_html_form(self, collection, field, language, name, value):
        value = value.split(";")
        while len(value) < 2:
            value.append('')
        return tal.getTAL(
                "metadata/date.html",
                dict(
                    date_format=field.metatype_data['format'],
                    name=name,
                    value=value,
                   ),
                macro="searchfield",
                language=language,
               )

    def viewer_get_data(self, metafield, maskitem, mask, node, language, html=True):
        ''' search with re if string could be a date
            appends this to a list and returns this

            :param metafield: metadatafield
            :param node: node with fields
            :return: formatted value
        '''
        value = node.get(metafield.getName())

        if not value or value == "0000-00-00T00:00:00":  # dummy for unknown
            return (metafield.getLabel(), u"")
        else:
            try:
                d = parse_date(value)
            except ValueError:
                return (metafield.getLabel(), value)
            value = format_date(d, format=metafield.metatype_data['format'])

        value_list = []

        if re.search(r'\d{2}\W\d{2}\W', value):
            day_month = re.sub(r'00\W', '', re.search(r'\d{2}\W\d{2}\W', value).group())
            value_list.append(day_month)

        if re.search(r'\d{4}\W\d{2}', value):
            year_month = re.sub(r'\W00', '', re.search(r'\d{4}-\d{2}', value).group())
            value_list.append(year_month)
        elif re.search(r'\d{4}', value):
            value_list.append(re.search(r'\d{4}', value).group())

        return (metafield.getLabel(), ''.join(value_list))

    def editor_parse_form_data(self, field, form):
        f = field.getSystemFormat(ustr(field.metatype_data['format']))
        if not f:
            return ""
        value = form.get(field.name)
        try:
            value = parse_date(ustr(value), f.value)
        except ValueError:
            return ""
        if not validateDate(value):
            return ""
        return format_date(value, format='%Y-%m-%dT%H:%M:%S')

    def admin_settings_get_html_form(self, fielddata, metadatatype, language):
        return tal.getTAL(
                "metadata/date.html",
                dict(
                    value=fielddata['format'],
                    dateoption=dateoption,
                   ),
                macro="metafieldeditor",
                language=language,
               )

    def admin_settings_parse_form_data(self, data):
        return dict(
            format=data["format"],
        )

    translation_labels = dict(
        de=dict(
            date_edit_date_format="Datums-/Zeitformat:",
            fieldtype_date="Datum",
            fieldtype_date_desc="Datumsauswahl (Tag / Monat / Jahr)",
        ),
        en=dict(
            date_edit_date_format="Date-/Time-format:",
            fieldtype_date="date",
            fieldtype_date_desc="date field (day / month / year)",
        ),
    )
