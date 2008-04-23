import core.tree as tree
import schema.schema as schema
import md5
import random

def edit_searchmask(req, ids):

    p2 = {}
    for k,v in req.params.items():
        if k.endswith(".x") or k.endswith(".y"):
            p2[k[:-2]] = v
        else:
            p2[k] = v
    req.params = p2

    openfield = None
    delfield = None
    delsubfield = None
    for k,v in req.params.items():
        if k.startswith("open_"):
            openfield = k[5:]
        if k.startswith("del_"):
            delfield = k[4:]
        if k.startswith("delsub_"):
            delsubfield = k[7:]
    print req.params

    node = tree.getNode(ids[0])

    root = tree.getRoot("searchmasks") 

    searchtype = req.params.get("searchtype", None)
    if not searchtype:
        searchtype = node.get("searchtype")
        if not searchtype:
            searchtype = "none"
            # if a parent has a search mask, use 'inherit'
            n = node
            while len(node.getParents()):
                n = node.getParents()[0]
                if n.get("searchtype") == "own":
                    searchtype = "parent"
    node.set("searchtype", searchtype)

    try:
        myschema = tree.getNode(req.params.get("schema", None))
    except tree.NoSuchNodeError:
        myschema = None
    try:
        schemafield = tree.getNode(req.params.get("schemafield", None))
    except tree.NoSuchNodeError:
        schemafield = None
    if myschema and schemafield and schemafield not in myschema.getChildren():
        print schemafield.name,"not in", myschema.name,": resetting"
        schemafield = None
    if schemafield and schemafield.type != "metafield":
        schemafield = None
   
    fields = None
    selectedfield = None

    if searchtype == "own":
        maskname = node.get("searchmaskname")
        if not maskname or not root.hasChild(maskname):
            while 1:
                maskname = md5.md5(str(random.random())).hexdigest()[0:8]
                if root.hasChild(maskname):
                    continue
                else:
                    break
            root.addChild(tree.Node(name=maskname, type="searchmask"))
            node.set("searchmaskname", maskname)
        mask = root.getChild(maskname)
        
        selectedfieldid = req.params.get("selectedfield", None)
        if selectedfieldid:
            # edit
            selectedfield = tree.getNode(selectedfieldid)
            assert selectedfield in mask.getChildren()
            selectedfield.setName(req.params["fieldname"])
            if "createsub" in req.params and schemafield:
                selectedfield.addChild(schemafield)
            if delsubfield:
                selectedfield.removeChild(tree.getNode(delsubfield))

        if req.params.get("isnewfield", "") == "yes":
            # create a new field
            l = mask.getNumChildren()
            mask.addChild(tree.Node("Suchfeld "+str(l), type="searchmaskitem"))
        elif delfield:
            # del a field
            delfield = tree.getNode(delfield)
            assert delfield in mask.getChildren()
            mask.removeChild(delfield)
        elif openfield:
            # unfold a new field
            selectedfieldid = openfield
        elif "close" in req.params:
            # fold a field
            selectedfieldid = None

        if selectedfieldid:
            selectedfield = tree.getNode(selectedfieldid)
            if selectedfield not in mask.getChildren():
                # this usually happens if the field was just deleted
                selectedfield = None
        else:
            selectedfield = None


        fields = mask.getChildren()

    data = {}
    data["idstr"] = ",".join(ids)
    data["node"] = node
    data["searchtype"] = searchtype
    data["schemas"] = schema.loadTypesFromDB()
    data["searchfields"] = fields
    data["selectedfield"] = selectedfield
    data["newfieldlink"] = "edit_content?id=%s&tab=tab_searchmask" % node.id
   
    if myschema:
        data["defaultschemaid"] = myschema.id
    else:
        data["defaultschemaid"] = None

    if schemafield:
        data["defaultfieldid"] = schemafield.id
    else:
        data["defaultfieldid"] = None

    data["schema"] = myschema

    def display(schemafield): 
        if not schemafield or schemafield.type != 'metafield':
            return 0
        if not schemafield.Searchfield():
            return 0
        if schemafield.get('type')=='union':
            return 0
        return 1
    data["display"] = display

    req.writeTAL("web/edit/edit_searchmask.html", data, macro="edit_metadata")

    return
