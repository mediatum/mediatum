import sys
sys.path += ["../", "."]
import core
import core.tree as tree

from core.acl import ACLParser
from tum.tumips import ubips, tumips

class Access:
    pass
a = Access()
a.ip = sys.argv[1]
p = ACLParser()

print "\n\nIP-Check for UB-IP's:"
x = p.parse("( iplist ubips )")
if x.has_access(a,None)==1:
    print " --> has access"
else:
    print " --> access denied for", sys.argv[1]
    
