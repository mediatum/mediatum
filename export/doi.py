# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from itertools import imap as map
from itertools import ifilter as filter
range = xrange

import base64 as _base64
import functools as _functools
import logging as _logging
import re as _re
import requests as _requests

import core as _core

_logg = _logging.getLogger(__name__)
_re_suffix = _re.compile(r"^[a-zA-Z0-9,._;()/-]+\Z").match

def registerdoi(node, mask, url, suffix, event, action):
    """
    Register/update a DOI with the DOI-server configured in mediatum.conf.
    node: The node that the DOI will reference (used for URL and metadata)
    suffix: The DOI suffix of the new DOI
    event: the requested state transition
    action: whether to update or create (or try both in that order) the DOI,
            one of "create", "update", "update-create"
    mask: optional, the name of the mask to be used to generate DataCite XML
          which is then used to update the DOI's metadata
    """
    assert event in (None, "publish", "register", "hide")
    assert action in ("create", "update", "update-create")
    assert _re_suffix(suffix)
    _logg.debug("registering doi '%s' to '%s' for node %s with'%s', event %s, action %s",
        suffix,
        url,
        node,
        "out a mask" if mask is None else " mask '{}'".format(mask),
        event,
        action,
        )

    if mask is None:
        data = dict()
    else:
        mask = node.metadatatype.getMask(mask)
        data = dict(xml=_base64.b64encode(mask.getViewHTML([node], flags=8).encode("utf-8")))
    data["doi"] = "{}/{}".format(_core.config.settings["doi-registration.prefix"], suffix)
    data["prefix"] = _core.config.settings["doi-registration.prefix"]
    if event is not None:
        data["event"] = event
    if url is not None:
        data["url"] = url

    with open(_core.config.settings["doi-registration.password-file"], "rb") as passwdfile:
        data = dict(
            auth=(_core.config.settings["doi-registration.username"], passwdfile.read().rstrip("\n")),
            json=dict(data=dict(type="dois", attributes=data)),
            )
    post = _functools.partial(_requests.post, url=_core.config.settings["doi-registration.api"], **data)
    put = _functools.partial(_requests.put, url="{}/{}/{}".format(
        _core.config.settings["doi-registration.api"].rstrip("/"),
        _core.config.settings["doi-registration.prefix"],
        suffix,
        ), **data)
    if action == "create":
        response = post()
    elif action == "update":
        response = put()
    elif action == "update-create":
        response = put()
        if response.status_code == 404:
            response = post()

    response.raise_for_status()
