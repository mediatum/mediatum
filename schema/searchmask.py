import core.tree as tree
import core.acl as acl
import hashlib
import random
from . import schema


class SearchMaskItem(tree.Node):

    def getFirstField(self):
        if self.getNumChildren():
            return self.getChildren()[0]
        return None


def newMask(node):
    root = tree.getRoot("searchmasks")
    while True:
        maskname = hashlib.md5(ustr(random.random())).hexdigest()[0:8]
        if root.hasChild(maskname):
            continue
        else:
            break
    mask = tree.Node(name=maskname, type="searchmask")
    root.addChild(mask)
    node.set("searchmaskname", maskname)
    return mask


def getMask(node):
    root = tree.getRoot("searchmasks")
    maskname = node.get("searchmaskname")
    if not maskname or not root.hasChild(maskname):
        return newMask(node)
    else:
        return root.getChild(maskname)


def getMainContentType(node):
    occurences = [(k, v) for k, v in node.getAllOccurences(acl.getRootAccess()).items()]
    occurences.sort(lambda x, y: cmp(y[1], x[1]))
    maintype = None
    for nodetype, num in occurences:
        if hasattr(nodetype, "isContainer") and not nodetype.isContainer():
            return nodetype
    return None


def generateMask(node):
    mask = getMask(node)

    maintype = getMainContentType(node)
    if not maintype:
        return

    # clean up
    for c in mask.getChildren():
        mask.removeChild(c)

    allfields = schema.getMetaType(maintype.getSchema())

    for metafield in maintype.getMetaFields("s"):

        d = metafield.get("label")
        if not d:
            d = metafield.getName()
        item = mask.addChild(tree.Node(d, type="searchmaskitem"))
        if metafield.get("type") == "union":
            for t in metafield.get("valuelist").split(";"):
                if t and allfields.hasChild(t):
                    item.addChild(allfields.getChild(t))
        else:
            item.addChild(metafield)

    return mask
