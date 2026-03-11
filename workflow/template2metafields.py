# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
This workflow step sets one or more attributes or columns of the current node
Attributes or columns: name, schema, type are provided by a xml-file linked to the node.
Structure of the xml-file:
<node-data>
  <metafield name="<attribute-name1>">attribute-value1</metafield>
  <metafield name="<attribute-name2>">attribute-value2</metafield>
  <metafield name="<attribute-name3>" clear="not-empty-string"/>  <!-- delete attribute-name3 -->
  <name>nodename</name>
  <schema>nodeschema</schema>
</node-data>

It is also possible to use tal expressions like:

  <metafield name="author" tal:content="python:'John' + ' ' + 'Doe'"></metafield>
"""

from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from itertools import imap as map
from itertools import ifilter as filter
range = xrange

import logging as _logging
import os as _os

import backports as _backports
import backports.functools_lru_cache as _
import lxml as _lxml
import mediatumtal as _mediatumtal
import mediatumtal.tal as _

import core as _core
import core.config as _
import core.nodecache as _
import utils as _utils
import utils.fileutils as _
import workflow as _workflow

_logg = _logging.getLogger(__name__)


def register():
    _workflow.registerStep("workflowstep_template2metafields")


@_backports.functools_lru_cache.lru_cache()
def _get_xml_validator():
    with open(_os.path.join(_os.path.dirname(__file__), 'template2metafields.relaxng.xml')) as f:
        return _lxml.etree.RelaxNG(_lxml.etree.parse(f)).assertValid


class WorkflowStep_Template2Metafields(_workflow.WorkflowStep):

    def runAction(self, node):
        with self.files[0].open() as f:
            data = _lxml.etree.fromstring(_mediatumtal.tal.getTALstr(f.read(), dict(node=node)).encode('utf-8'))
        _get_xml_validator()(data)
        metadatatypes = _core.nodecache.get_metadatatypes_node()
        for element in data.findall('metafield'):
            if element.get("clear"):
                node.attrs.pop(element.get("name"), None)
            else:
                node.attrs[element.get("name")] = element.text or ""
        if data.find('name') is not None:
            node.name = data.find('name').text or ""
        nodeschema = (data.find('schema').text or '') if data.find('schema') is not None else node.schema
        if node.type not in metadatatypes.children.filter_by(name=nodeschema).one().getDatatypes():
            raise RuntimeError("bad schema/type combination")
        node.schema = nodeschema

        _core.db.session.commit()
        self.forward(node, True)

    def admin_settings_get_html_form(self, req):
        files = tuple(f for f in self.files if f.filetype=="wfstep-template2metafields")
        if len(files) == 1:
            context = dict(
                    filebasename=files[0].base_name,
                    filesize=files[0].size,
                    fileurl=u'/file/{}/{}'.format(self.id, files[0].base_name),
                   )
        else:
            context = dict(filebasename=None, filesize=None, fileurl=None)
        return _mediatumtal.tal.processTAL(
            context,
            file="workflow/template2metafields.html",
            macro="workflow_step_type_config",
            request=req,
           )

    def admin_settings_save_form_data(self, data):
        data = data.to_dict()
        tal_template = data.pop('tal-template', None)
        if tal_template:
            for f in self.files:
                self.files.remove(f)
            self.files.append(_utils.fileutils.importFile(
                _utils.fileutils.sanitize_filename(tal_template.filename),
                tal_template,
                filetype="wfstep-template2metafields",
               ))
        self.settings = data
        _core.db.session.commit()
