"""menusortnodes submenu removed from editor menu

Revision ID: 6cd40ed911a7
Revises: 59f52be1072d
Create Date: 2019-07-30 16:40:13.566650

"""

# revision identifiers, used by Alembic.
from __future__ import division

revision = '6cd40ed911a7'
down_revision = '59f52be1072d'
branch_labels = None
depends_on = None

from alembic import op
from sqlalchemy.sql import text


def upgrade():
    data = op.get_bind().execute("select system_attrs from node where id =1")
    row = data.fetchone()

    data = op.get_bind().execute("select system_attrs from node where id =1")
    row = data.fetchone()

    menu_layout_dir = "content;metadata;menuoperation(acls;menueditall(editall;moveall;copyall;deleteall);menunodesperpage(nodesperpage20;nodesperpage50;nodesperpage100;nodesperpage200);startpagesmenu(startpages;logo;searchmask);admin;subfolder;sortfiles)"
    menu_layout_file = "parentcontent;view;metadata;files;menuoperation(acls;classes;changeschema;menueditobject(moveobject;copyobject;deleteobject);admin)"

    for key, value in row[0].items():
        if not (key.startswith('edit.menu') and (key != 'edit.menu.default')):
            continue
        op.get_bind().execute(
            text("update mediatum.node set system_attrs = jsonb_set(system_attrs, :key,:value) where id=1;"),
            key="{{{}}}".format(key),
            value='"{}"'.format(menu_layout_dir if "startpages" in value else menu_layout_file),
        )


def downgrade():
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
