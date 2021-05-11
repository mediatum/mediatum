# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
metafield change valuelist to metatype-data

Revision ID: f6f331204e0b
Revises: fe4320dc9cf4
Create Date: 2022-04-13 09:26:13.139333
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
import schema.schema as _schema


# revision identifiers, used by Alembic.
revision = 'f6f331204e0b'
down_revision = '5865227ae87a'
branch_labels = None
depends_on = None


_metatypes = dict(
        date=dict(keys=("format",)),
        dlist=dict(keys=("data_address", "data_type", "attribute", "value", "selection_format")),
        hlist=dict(
            downgrade=dict(onlylast=lambda v:"1" if v else ""),
            keys=("parentnode", "attrname", "onlylast"),
            upgrade=dict(onlylast=bool),
           ),
        htmlmemo=dict(
            downgrade=dict(max_length=lambda v: str(v or "")),
            keys=("max_length",),
            upgrade=dict(max_length=lambda v:int(v) if v else None),
           ),
        memo=dict(
            downgrade=dict(max_length=lambda v:str(v or "")),
            keys=("max_length",),
            upgrade=dict(max_length=lambda v:int(v) if v else None),
           ),
        meta=dict(
            downgrade=dict(synchronize=lambda v:"on" if v else ""),
            keys=("fieldname", "synchronize"),
            upgrade=dict(synchronize=lambda v:v=="on"),
           ),
        url=dict(
            downgrade=dict(new_window=lambda v: "_blank" if v else "same"),
            keys=("link", "text", "icon", "new_window"),
            upgrade=dict(new_window=lambda v:v in ("", "_blank")),
           ),
        # these need special treatment
        list=NotImplemented,
        mlist=NotImplemented,
       )


def upgrade():
    for metafield in _core.db.query(_schema.Metafield).prefetch_attrs():
        metatype = metafield.get("type")
        data = metafield.attrs.pop("valuelist", "")
        data = data.replace(";", "\r\n").split("\r\n")
        if metatype=="mlist":
            data = dict(listelements=data)
        elif metatype=="list":
            data = dict(
                    listelements=data,
                    multiple=bool(metafield.attrs.pop("multiple", False)),
                   )
        elif metatype in _metatypes:
            keys = _metatypes[metatype]["keys"]
            data.extend(("",)*len(keys))
            data = dict(zip(keys, data[:len(keys)]))
            for key,convert in _metatypes[metatype].get("upgrade",{}).iteritems():
                data[key] = convert(data[key])
        else:  # metatypes without real settings
            data = None
        metafield.metatype_data = data
    _core.db.session.commit()


def downgrade():
    for metafield in _core.db.query(_schema.Metafield).prefetch_attrs():
        metatype = metafield.get("type")
        data = metafield.metatype_data
        metafield.attrs.pop("metatype-data")
        if metatype=="mlist":
            data = "\r\n".join(data["listelements"])
        elif metatype=="list":
            metafield.set("multiple", "1" if data["multiple"] else None)
            data = "\r\n".join(data["listelements"])
        elif metatype in _metatypes:
            keys = _metatypes[metatype]["keys"]
            for key,convert in _metatypes[metatype].get("downgrade",{}).iteritems():
                data[key] = convert(data[key])
            data = ";".join(v for v in map(data.get,keys))
        else:
            continue
        metafield.set("valuelist", data)
    _core.db.session.commit()
