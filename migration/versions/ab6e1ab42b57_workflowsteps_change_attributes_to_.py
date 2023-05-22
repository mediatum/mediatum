# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""workflowsteps_change_attributes_to_workflowstep_settings

Revision ID: ab6e1ab42b57
Revises: defeedf3b29a
Create Date: 2022-11-08 06:28:07.525205

"""

from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from itertools import imap as map
from itertools import ifilter as filter
range = xrange

import os as _os
import sys as _sys

_sys.path.append(_os.path.abspath(_os.path.join(_os.path.dirname(__file__), "../..")))

import core as _core
import core.init as _core_init
_core_init.full_init()

import workflow.workflow as _workflow


# revision identifiers, used by Alembic.
revision = 'ab6e1ab42b57'
down_revision = 'defeedf3b29a'
branch_labels = None
depends_on = None


_workflowstep_keys = dict(
        addformpage={
            "pdf_fields_editable": "fields_editable",
            "pdf_form_separate": "form_separate",
            "pdf_form_overwrite": "form_overwrite",
           },
        checkcontent={"email": "recipient", "from": "sender"},
        defer={"body": None, "subject": None, "recipient": None},
        publish={
            "publishsetpublishedversion": "set_version",
            "publishsetupdatetime": "set_updatetime",
           },
        sendemail={"email": "recipient", "from": "sender", "sendcondition": None},
        start={"newnodetype": "schemas", "starttext": "starthtmltext"},
        textpage={"text": "htmltext"},
        upload={"prefix": None, "suffix": None, "singleobj": None},
       )


def upgrade():
    for wfstep_cls in _workflow.WorkflowStep.__subclasses__():
        wfstep_name = wfstep_cls.__name__.lower()[13:]
        wfstep_keys = _workflowstep_keys.get(wfstep_name, {})
        wfstep_default_settings = wfstep_cls.default_settings or {}
        if not (wfstep_default_settings or wfstep_keys):
            continue
        for wfstep in _core.db.query(wfstep_cls).prefetch_attrs():
            attrs = wfstep.attrs

            # handle special cases that cannot be handled by `_workflowstep_keys`
            if (wfstep_name == "deletefile") and (attrs.get("filetype") == "*"):
                attrs["filetype"] = ""

            for old, new in wfstep_keys.iteritems():
                if old in attrs:
                    old = attrs.pop(old)
                    if new:
                        attrs[new] = old

            settings = dict() if wfstep_default_settings else None
            for name, default in wfstep_default_settings.iteritems():
                if isinstance(default, tuple):
                    value = attrs.pop(name, None)
                    settings[name] = tuple(filter(None, value.split(';'))) if value else default
                elif isinstance(default, str) or isinstance(default, unicode) or default is None:
                    settings[name] = attrs.pop(name, default)
                elif isinstance(default, bool):
                    settings[name] = bool(attrs.pop(name, default))
                else:
                    raise AssertionError("unknown settings type")

            wfstep.settings = settings
    _core.db.session.commit()


def downgrade():
    for wfstep_cls in _workflow.WorkflowStep.__subclasses__():
        wfstep_name = wfstep_cls.__name__.lower()[13:]
        wfstep_keys = _workflowstep_keys.get(wfstep_name, {})
        wfstep_default_settings = wfstep_cls.default_settings or {}
        if not (wfstep_default_settings or wfstep_keys):
            continue
        for wfstep in _core.db.query(wfstep_cls).prefetch_attrs():
            attrs = wfstep.attrs
            settings = wfstep.settings
            attrs.pop("workflowstep-settings")

            for name, default in wfstep_default_settings.iteritems():
                if isinstance(default, tuple):
                    attrs[name] = ";".join(settings[name])
                elif isinstance(default, str):
                    attrs[name] = settings[name]
                elif default is None:
                    if settings[name] is not None:
                        attrs[name] = settings[name]
                elif isinstance(default, bool):
                    attrs[name] = "1" if settings[name] else ""
                else:
                    raise AssertionError("unknown settings type")

            del settings

            for old, new in wfstep_keys.iteritems():
                # we turn `new` into `old` here!
                attrs[old] = attrs.pop(new, "") if new else ""

            # handle special cases that cannot be handled by `_workflowstep_keys`
            if (wfstep_name == "deletefile") and (attrs["filetype"] == ""):
                attrs["filetype"] = "*"

    _core.db.session.commit()
