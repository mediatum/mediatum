import core.tree as tree
import schema.schema as schema

def edit_searchmask(req, ids):

    node = tree.getNode(ids[0])

    searchtype = req.params.get("searchtype", None)
    if not searchtype:
        searchtype = node.get("searchtype")
        if not searchtype:
            searchtype = "none"

    fields = tree.getNode("634935").getChildren()

    data = {}
    data["idstr"] = ",".join(ids)
    data["node"] = node
    data["searchtype"] = searchtype
    data["schemas"] = schema.loadTypesFromDB()
    data["searchfields"] = fields
    data["selectedfield"] = fields[0]

    req.writeTAL("web/edit/edit_searchmask.html", data, macro="edit_metadata")

    return
