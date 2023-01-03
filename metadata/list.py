# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import collections as _collections
import cStringIO as _cStringIO

from mediatumtal import tal
import ruamel.yaml as _ruamel_yaml

from utils.utils import esc
from core.metatype import Metatype
from core import db
import metadata.common_list as _common_list

q = db.query

_Element = _collections.namedtuple("_Element", "label optgroup indent count selected");
# label: just the name from the elements list
# indent: number of spaces before the label
# counts: number of occurences in the data base (to be displayed in parentheses)
# optgroup: True/False
# selected: True/False

def _format_elements(elements, selected_elements=frozenset(), counts={}, _indent=0):
    for element in elements:
        if not isinstance(element, _collections.Mapping):
            assert element >= ""
            element = dict(
                name=element,
                selectable=True,
                subelements=(),
               )
        yield _Element(
                count=counts.get(element["name"]) if element["selectable"] else None,
                indent=_indent,
                label=element["name"],
                optgroup=not element["selectable"],
                selected=element["selectable"] and (element["name"] in selected_elements),
               )
        for e in _format_elements(element["subelements"], selected_elements, counts, _indent=_indent+1):
            yield e


class m_list(Metatype):

    name = "list"

    default_settings = dict(
        listelements=(),
        multiple=False,
    )

    def get_default_value(self, field):
        element = next(_format_elements(field.metatype_data["listelements"]))
        if not element.optgroup:
            return element.label

    def editor_get_html_form(self, field, value="", width=400, lock=0, language=None, required=None):
        return tal.getTAL(
                "metadata/list.html",
                dict(
                    field=field,
                    lock=lock,
                    multiple=field.metatype_data['multiple'],
                    name=field.getName(),
                    required=1 if required else None,
                    elements=tuple(_format_elements(
                            field.metatype_data["listelements"],
                            selected_elements=frozenset(value.split(";")),
                           )),
                    width=width,
                  ),
                macro="editorfield",
                language=language,
               )

    def search_get_html_form(self, collection, field, language, name, value):
        return tal.getTAL(
                "metadata/list.html",
                dict(
                    name=name,
                    elements=tuple(_format_elements(
                            field.metatype_data["listelements"],
                            selected_elements=frozenset((value,)),
                            counts=dict(_common_list.count_list_values_for_all_content_children(
                                    collection.id,
                                    field.getName(),
                                   )),
                           )),
                   ),
                macro="searchfield",
                language=language,
               )

    def viewer_get_data(self, metafield, maskitem, mask, node, language, html=True):
        value = node.get(metafield.getName()).replace(";", "; ")
        if html:
            value = esc(value)
        return (metafield.getLabel(), value)

    def editor_parse_form_data(self, field, form):
        if field.metatype_data['multiple']:
            valuelist = form.getlist(field.name)
            value = ";".join(valuelist)
        else:
            value = form.get(field.name)
        return value.replace("; ", ";")

    def admin_settings_get_html_form(self, fielddata, metadatatype, language):
        output = _cStringIO.StringIO()
        yaml = _ruamel_yaml.YAML(typ="safe", pure=True)
        yaml.indent(mapping=2, sequence=4, offset=2)
        yaml.default_flow_style = False
        yaml.dump(fielddata['listelements'], output)
        return tal.getTAL(
            "metadata/list.html",
            dict(
                    multiple_list=fielddata['multiple'],
                    value=output.getvalue().replace('\n', '\r\n'),
               ),
            macro="metafieldeditor",
            language=language,
        )

    def admin_settings_parse_form_data(self, data):
        if "listelements" in data:
            listelements = _ruamel_yaml.YAML(typ="safe", pure=True).load(data["listelements"])
        else:
            listelements = ()

        assert data.get("multiple") in (None, "1")
        return dict(
            listelements=listelements,
            multiple=bool(data.get("multiple")),
        )
