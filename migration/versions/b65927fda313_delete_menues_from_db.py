"""delete_menues_from_db

Revision ID: b65927fda313
Revises: 5f09bbe431bb
Create Date: 2020-05-06 09:20:34.390438

"""

# revision identifiers, used by Alembic.
from __future__ import division
from __future__ import print_function

revision = 'b65927fda313'
down_revision = '5f09bbe431bb'
branch_labels = None
depends_on = None

from alembic import op
from sqlalchemy.sql import text

def upgrade():
    # Drop 'edit.menu' in system_attrs
    connection = op.get_bind()
    results = connection.execute(
        text("SELECT key FROM mediatum.node, lateral jsonb_each_text(system_attrs) WHERE id=1 AND key LIKE 'edit.menu%';")).fetchall()
    for akey in results:
        connection.execute(
            text("update mediatum.node set system_attrs = system_attrs - '" + akey[0] + "' where id=1;")
        )
    # Drop admin.menu
    connection.execute(
        text("update mediatum.node set system_attrs = system_attrs - 'admin.menu' where id=1;")
    )

def downgrade():
    menu_dir_items = ['collection', 'collections', 'directory', 'project', 'directoryarmus', 'directoryarmusarch', 'directoryarmusproject']
    menu_file_items = ['audio', 'dissertation', 'document', 'file', 'image', 'video']
    menu_layout_dir = "content;metadata;menuoperation(acls;menueditall(editall;moveall;copyall;deleteall);menunodesperpage(nodesperpage20;nodesperpage50;nodesperpage100;nodesperpage200);menusortnodes(sortnodes);files;startpagesmenu(startpages;logo;searchmask);admin)"
    menu_layout_file = "parentcontent;view;metadata;files;menuoperation(acls;classes;changeschema;menueditobject(moveobject;copyobject;deleteobject);admin)"
    menu_layout_admin = "menumain();menudata(mapping;metatype);menuworkflow(workflows);menusystem(settingsmenu)"
    for akey in menu_dir_items:
        op.get_bind().execute(
            text("update mediatum.node set system_attrs = system_attrs || jsonb_set(system_attrs, :key,:value) where id=1;"),
            key="{{{}}}".format("edit.menu."+akey),
            value='"{}"'.format(menu_layout_dir),
        )
    for akey in menu_file_items:
        op.get_bind().execute(
            text("update mediatum.node set system_attrs = system_attrs || jsonb_set(system_attrs, :key,:value) where id=1;"),
            key="{{{}}}".format("edit.menu."+akey),
            value='"{}"'.format(menu_layout_file),
        )
    op.get_bind().execute(
        text("update mediatum.node set system_attrs = system_attrs || jsonb_set(system_attrs, :key,:value) where id=1;"),
        key="{{{}}}".format("admin.menu"),
        value='"{}"'.format(menu_layout_admin),
    )
