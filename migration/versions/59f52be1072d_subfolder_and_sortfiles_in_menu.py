"""subfolder and sortfiles in menu

Revision ID: 59f52be1072d
Revises: e756951fa48e
Create Date: 2019-07-16 12:36:26.891141

"""

# revision identifiers, used by Alembic.
from __future__ import division

revision = '59f52be1072d'
down_revision = 'e756951fa48e'
branch_labels = None
depends_on = None

from alembic import op
from sqlalchemy.sql import text


def upgrade():
    data = op.get_bind().execute("select system_attrs from node where id =1")
    row = data.fetchone()

    menu_layout_dir = "content;metadata;menuoperation(acls;menueditall(editall;moveall;copyall;deleteall);menunodesperpage(nodesperpage20;nodesperpage50;nodesperpage100;nodesperpage200);menusortnodes(sortnodes);files;startpagesmenu(startpages;logo;searchmask);admin;subfolder;sortfiles)"

    for key, value in row[0].items():
        if not (key.startswith('edit.menu') and (key != 'edit.menu.default')):
            continue
        if ("startpages" in value):
            op.get_bind().execute(
                text("update mediatum.node set system_attrs = jsonb_set(system_attrs, :key,:value) where id=1;"),
                key="{{{}}}".format(key),
                value='"{}"'.format(menu_layout_dir),
            )


def downgrade():
    data = op.get_bind().execute("select system_attrs from node where id =1")
    row = data.fetchone()

    menu_layout_dir = "content;metadata;menuoperation(acls;menueditall(editall;moveall;copyall;deleteall);menunodesperpage(nodesperpage20;nodesperpage50;nodesperpage100;nodesperpage200);menusortnodes(sortnodes);files;startpagesmenu(startpages;logo;searchmask);admin)"
    menu_layout_file = "parentcontent;view;metadata;files;menuoperation(acls;classes;changeschema;menueditobject(moveobject;copyobject;deleteobject);admin)"

    for key, value in row[0].items():
        if not (key.startswith('edit.menu') and (key != 'edit.menu.default')):
            continue
        op.get_bind().execute(
            text("update mediatum.node set system_attrs = jsonb_set(system_attrs, :key,:value) where id=1;"),
            key="{{{}}}".format(key),
            value='"{}"'.format(menu_layout_dir if "startpages" in value else menu_layout_file),
        )

