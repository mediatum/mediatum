import json
from mediatumtal import tal
from core.metatype import Metatype
from core.transition import httpstatus
from core import Node
from core import db

q = db.query


class m_hlist(Metatype):

    def getMaskEditorHTML(self, field, metadatatype=None, language=None, required=None):
        try:
            values = field.get("valuelist").split(u';')
        except AttributeError:
            try:
                values = field.split(u'\r\n')
            except AttributeError:
                values = []

        while len(values) < 3:
            values.append(u'')
        return tal.getTAL("metadata/hlist.html", {"value": dict(parentnode=values[0], attrname=values[1], onlylast=values[2])}, macro="maskeditor", language=language)

    def getEditorHTML(self, field, value="", width=40, lock=0, language=None, required=None):
        try:
            values = field.get("valuelist").split(';')
        except AttributeError:
            values = field.split('\r\n')
        while len(values) < 3:
            values.append(u'')
        return tal.getTAL("metadata/hlist.html", {"lock": lock, "startnode": values[0], "attrname": values[1], "onlylast": values[2], "value": value, "width": width, "name": field.getName(), "field": field, "required": self.is_required(required)}, macro="editorfield", language=language)

    def getFormattedValue(self, metafield, maskitem, mask, node, language, html=True):
        value = []
        ids = node.get(metafield.getName())
        if ids:
            for n in ids.split(';'):
                vn = q(Node).get(n)
                if vn is not None:
                    value.append(vn.getName())
        values = metafield.get("valuelist").split(';')
        while len(values) < 3:
            values.append(u'')
        if values[2] == '1':
            return metafield.getLabel(), value[-1]
        return metafield.getLabel(), u' - '.join(value)

    def getName(self):
        return "fieldtype_hlist"

    def getInformation(self):
        return {"moduleversion": "1.0", "softwareversion": "1.1"}

    def getPopup(self, req):
        children = dict()
        attrfilter = req.args.get(u'attrfilter')
        pidlist = req.args.get(u'id').split(u'|')

        def getAllContainerChildren(node, attrfilter=attrfilter):
            from contenttypes import Container
            nodes = node.all_children_by_query(q(Container).filter(Node.a[attrfilter] != ''))
            return nodes

        # try direct container children
        childlist = []
        for _id in pidlist:
            childlist.extend(filter(lambda c: c and (c.get(attrfilter) != u""), q(Node).get(_id).children))

        for child in childlist:
            children[child.id] = child.getName()

        # if no direct children test all container children
        if len(children) == 0:
            for _id in pidlist:
                for child in getAllContainerChildren(q(Node).get(_id)):
                    children[child.id] = child.getName()

        req.write(json.dumps(children))
        return httpstatus.HTTP_OK

    # method for additional keys of type mlist
    def getLabels(self):
        return m_hlist.labels

    labels = {"de":
              [
                  ("fieldtype_hlist", "Hierarchische Werteliste"),
                  ("fieldtype_hlist_desc", "Hierarchische Werteliste aus Attributwerten"),
                  ("hlist_edit_parentnodes", "Basisknoten:"),
                  ("hlist_edit_attrname", "Attributname:"),
                  ("hlist_edit_onlylast", "Zeige nur Kindknoten:")
              ],
              "en":
              [
                  ("fieldtype_hlist", "Hierarchical list"),
                  ("fieldtype_hlist_desc", "Hierarchical list from attributes"),
                  ("hlist_edit_parentnodes", "Base node:"),
                  ("hlist_edit_attrname", "Attribute name:"),
                  ("hlist_edit_onlylast", "Show only child:")
              ]
              }
