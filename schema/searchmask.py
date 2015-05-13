import core.acl as acl
import hashlib
import random
from . import schema
from core.transition.postgres import check_type_arg
from core import Node
from core import db
from contenttypes import Home, Collections
from core.systemtypes import Root, Searchmasks

q = db.query

class SearchMask(Node):
    pass

@check_type_arg
class SearchMaskItem(Node):

    def getFirstField(self):
        if len(self.children):
            return self.children[0]
        return None


def newMask(node):
    searchmask_root = q(Searchmasks).one()
    while True:
        maskname = unicode(hashlib.md5(ustr(random.random())).hexdigest()[0:8])
        if maskname in searchmask_root.children.all():
            continue
        else:
            break
    mask = Node(name=maskname, type=u"searchmask")
    searchmask_root.children.append(mask)
    node.set("searchmaskname", maskname)
    return mask


def getMask(node):
    maskname = node.get("searchmaskname")
    mask = q(Searchmasks).one().children.filter_by(name=maskname).scalar()
    if not maskname or mask is None:
        return newMask(node)
    else:
        return mask


def getMainContentType(node):
    #todo this needs acl checks
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
    for field in mask.children:
        mask.children.remove(field)

    allfields = schema.getMetaType(maintype.getSchema())
    q(Metadatatype).filter_by(name=name).scalar()

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

    db.session.commit()
    return mask