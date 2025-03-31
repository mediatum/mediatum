# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import logging
import os as _os
import re

import backports.functools_lru_cache as _backports_functools_lru_cache
import ruamel.yaml as _ruamel_yaml

import mediatumtal.tal as _tal

import core as _core
from .workflow import WorkflowStep, registerStep
import utils.date as date
from core import config as _core_config

logg = logging.getLogger(__name__)


@_backports_functools_lru_cache.lru_cache(maxsize=None)
def _get_chkmap():
    with open(_os.path.join(_core_config.basedir, "workflow", "urn-checksum-map.yaml"), "rb") as f:
        return _ruamel_yaml.YAML(typ="safe", pure=True).load(f).get


def _build_checksum(urn):
    i = 1
    digit = "0"
    sum = 0

    for char in urn:
        for digit in str(_get_chkmap()(char, "")):
            sum += int(digit) * i
            i = i + 1
    return ustr(sum // int(digit))[-1:]


def _build_bnb(snid1, snid2, niss):
    # ----- urn structure -----
    # urn:<NID>:<NID-specific Part>
    #
    # NID - Namespace IDentifier
    # The complete list of Univorm Resource Names Namespaces
    # can be referenced here:
    # http://www.iana.org/assignments/urn-namespaces/urn-namespaces.xml

    urn = "urn:" + ustr(snid1) + ":" + ustr(snid2) + "-" + niss + "-"
    return urn + _build_checksum(urn)


def _increase_urn(urn):
    checksum = 0
    dashes = 0
    if urn.startswith("urn:nbn"):
        # nbn urns have a checksum digit at the end
        checksum = 1
        urn = urn[0:-1]
    while urn.endswith("-"):
        dashes += 1
        urn = urn[:-1]
    # increate the urn, starting with the last number
    i = len(urn) - 1
    add1 = 1
    while add1:
        add1 = 0
        if i >= 0 and ord('0') <= ord(urn[i]) <= ord('9'):
            newnr = ord(urn[i]) + 1
            if newnr > ord('9'):
                add1 = 1
                newnr = ord('0')
            urn = urn[0:i] + chr(newnr) + urn[i + 1:]
        else:
            urn = urn[0:i + 1] + '0' + urn[i + 1:]
        i = i - 1
    urn += "-" * dashes
    if checksum:
        # re-add checksum digit
        urn += _build_checksum(urn)
    return urn


def register():
    registerStep("workflowstep_urn")


class WorkflowStep_Urn(WorkflowStep):

    default_settings = dict(
        attrname="urn",
        snid1="",
        snid2="",
        niss="",
    )

    def runAction(self, node, op=""):
        attrname = self.settings["attrname"]
        niss = self.settings["niss"]
        urn = node.get(attrname)

        if urn:
            node.set(attrname, _increase_urn(node.get(attrname)))
        else:
            for var in re.findall(r'\[(.+?)\]', niss):
                if var == "att:id":
                    niss = niss.replace("[" + var + "]", unicode(node.id))
                elif var.startswith("att:"):
                    val = node.get(var[4:])
                    try:
                        val = date.format_date(date.parse_date(val), '%Y%m%d')
                    except:
                        logg.exception("exception in workflow step urn, date formatting failed, ignoring")

                    niss = niss.replace("[" + var + "]", val)
            node.set(attrname, _build_bnb(self.settings["snid1"], self.settings["snid2"], niss))
        _core.db.session.commit()
        return self.forward(node, True)

    def admin_settings_get_html_form(self, req):
        return _tal.processTAL(
            self.settings,
            file="workflow/urn.html",
            macro="workflow_step_type_config",
            request=req,
           )

    def admin_settings_save_form_data(self, data):
        data = data.to_dict()
        assert frozenset(data) == frozenset(("attrname", "snid1", "snid2", "niss"))
        self.settings = data
        _core.db.session.commit()
