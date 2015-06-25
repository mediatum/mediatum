from core import config
import core.init as initmodule
from functools import wraps

from core import init
import core.database
from core.database.postgres.node import t_noderelation
init.basic_init()
# we don't want to raise exceptions for missing node classes
init.check_undefined_nodeclasses()

from core import Node
from core import File

q = core.db.query
s = core.db.session


from core import User
gampfer = q(User).get(1063371)
from core import athana
req = athana.http_request(None, None, None, '/', None, None)
req.ip = '127.0.0.1'
req.session = {}

s.execute("set search_path to mediatum")
s.commit()

access_types = ["read", "write", "data"]

nn = q(Node).get(4651)
req.session["user"] = gampfer
node_ids = [n.id for n in nn.content_children.filter_read_access(req).limit(10)]
first_node = node_ids[0]
print "user gampfer ids", node_ids
print "gampfer has access? read {} write {} data {}".format(*[Node.req_has_access_to_node_id(first_node, a, req) for a in access_types])


req.session["user"] = q(User).filter_by(display_name=u"Gast").one()
print "user Gast", [n.id for n in nn.content_children.filter_read_access(req).limit(10)]
print "Gast has access? read {} write {} data {}".format(*[Node.req_has_access_to_node_id(first_node, a, req) for a in access_types])

# print [t[0] for t in q(Node.id).filter_read_access(req).limit(10)]
