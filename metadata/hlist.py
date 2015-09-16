import json
import core.tree as tree
from mediatumtal import tal
from core.metatype import Metatype
from core.transition import httpstatus


class m_hlist(Metatype):

    def getMaskEditorHTML(self, field, metadatatype=None, language=None, required=None):
        try:
            values = field.valuelist.split(u';')
        except AttributeError:
            try:
                values = field.split(u'\r\n')
            except AttributeError:
                values = []
        except UnicodeDecodeError:
            values = field.valuelist.split(';')

        while len(values) < 3:
            values.append(u'')
        return tal.getTAL("metadata/hlist.html", {"value": dict(parentnode=values[0], attrname=values[1], onlylast=values[2])}, macro="maskeditor", language=language)

    def getEditorHTML(self, field, value="", width=40, lock=0, language=None, required=None):
        try:
            values = field.valuelist.split(';')
        except AttributeError:
            values = field.split('\r\n')
        while len(values) < 3:
            values.append(u'')
        return tal.getTAL("metadata/hlist.html", {"lock": lock, "startnode": values[0], "attrname": values[1], "onlylast": values[2], "value": value, "width": width, "name": field.getName(), "field": field, "required": self.is_required(required)}, macro="editorfield", language=language)

    def getFormatedValue(self, field, node, language=None, html=1, template_from_caller=None, mask=None):
        value = []
        for n in node.get(field.getName()).split(';'):
            try:
                value.append(tree.getNode(n).getName())
            except tree.NoSuchNodeError:
                pass
        values = field.valuelist.split(';')
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
            for n in node.getContainerChildren():
                nodes = getAllContainerChildren(n, nodes)
            nodes.extend(filter(lambda c: c.get(req.args.get(u'attrfilter')) != u"", node.getContainerChildren()))
            return nodes

        # try direct container children
        childlist = []
        for _id in req.args.get('id').split('|'):
            try:
                childlist.extend(filter(lambda c: c.get(req.args.get(u'attrfilter')) != u"", tree.getNode(_id).getChildren()))
            except tree.NoSuchNodeError:
                pass
        for child in childlist:
            children[child.id] = child.getName()
        # if no direct children test all container children
        if len(children) == 0:
            for _id in req.args.get('id').split('|'):
                try:
                    for child in getAllContainerChildren(tree.getNode(_id)):
                        children[child.id] = child.getName()
                except tree.NoSuchNodeError:
                    pass

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
