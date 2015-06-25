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

    def getFormatedValue(self, field, node, language=None, html=1, template_from_caller=None, mask=None):
        value = []
        for n in node.get(field.getName()).split(';'):
            vn = q(Node).get(n)
            if vn is not None:
                value.append(vn.getName())
        values = field.get("valuelist").split(';')
        while len(values) < 3:
            values.append(u'')
        if values[2] == '1':
            return field.getLabel(), value[-1]
        return field.getLabel(), ' - '.join(value)

    def getName(self):
        return "fieldtype_hlist"

    def getInformation(self):
        return {"moduleversion": "1.0", "softwareversion": "1.1"}

    def getPopup(self, req):
        children = dict()

        def getAllContainerChildren(node, nodes=list()):
            for n in node.container_children:
                nodes = getAllContainerChildren(n, nodes)
            nodes.extend(filter(lambda c: c.get(req.args.get(u'attrfilter')) != u"", node.container_children))
            return nodes

        # try direct conteiner children
        for child in filter(lambda c: c.get(req.args.get(u'attrfilter')) != u"", q(Node).get(req.args.get(u'id')).children):

            children[child.id] = child.getName()
        # if no direct children test all container children
        if len(children) == 0:
            for child in getAllContainerChildren(q(Node).get(req.args.get(u'id'))):
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
