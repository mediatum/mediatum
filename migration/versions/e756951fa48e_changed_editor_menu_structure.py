"""Changed editor menu structure

Revision ID: e756951fa48e
Revises: 73d8e632ec3a
Create Date: 2019-06-06 15:14:13.776791

"""

# revision identifiers, used by Alembic.
from __future__ import division
from __future__ import print_function

revision = 'e756951fa48e'
down_revision = '73d8e632ec3a'
branch_labels = None
depends_on = None

from alembic import op
from sqlalchemy.sql import text

def upgrade():
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


def downgrade():
    data = op.get_bind().execute("select system_attrs from node where id =1")
    row = data.fetchone()

    menu_layout_dir = "menulayout(content;startpages);menumetadata(metadata;logo;files;admin;searchmask;sortfiles);menusecurity(acls);menuoperation(subfolder;statsaccess;statsfiles;changeschema)"
    menu_layout_file = "menulayout(view);menumetadata(metadata;files;admin);menuclasses(classes);menusecurity(acls);menuoperation(changeschema)"
    menu_layouts = dict(
        # dirs
        collection="menulayout(content;startpages);menumetadata(metadata;logo;files;admin;searchmask;sortfiles);menusecurity(acls);menuoperation(subfolder;statsaccess;statsfiles;changeschema)",
        directory="menulayout(content;startpages);menumetadata(metadata;files;admin);menusecurity(acls);menuoperation(subfolder;changeschema)",
        collections="menulayout(content;startpages);menumetadata(metadata;logo;admin;searchmask;sortfiles;files);menusecurity(acls);menuoperation(subfolder;statsaccess;statsfiles)",
        # files
        audio="menulayout(view);menumetadata(metadata;files;admin);menuclasses(classes);menusecurity(acls);menuoperation(changeschema)",
        video="menulayout(view);menumetadata(metadata;files;admin);menuclasses(classes);menusecurity(acls);menuoperation(changeschema)",
        image="menulayout(view);menumetadata(metadata;files;admin);menuclasses(classes);menusecurity(acls);menuoperation(changeschema)",
        document="menulayout(view);menumetadata(metadata;files;admin);menuclasses(classes);menusecurity(acls);menuoperation(changeschema;identifier)",
        file="menuglobals();menulayout(view);menumetadata(metadata;files;admin);menuclasses(classes);menusecurity(acls);menuoperation()",
    )
    for key, value in row[0].items():
        if not (key.startswith('edit.menu') and (key != 'edit.menu.default')):
            continue
        _1,_2,menu_type = key.split(".",2)
        op.get_bind().execute(
            text("update mediatum.node set system_attrs = jsonb_set(system_attrs, :key,:value) where id=1;"),
            key="{{{}}}".format(key),
            value='"{}"'.format(menu_layouts.get(menu_type, menu_layout_dir if "startpages" in value else menu_layout_file)),
        )
