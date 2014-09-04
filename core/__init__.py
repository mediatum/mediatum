import os
import sys

editmodulepaths = [('', 'web/edit/modules')]

from core import config

print "Python Version is", sys.version.split("\n")[0]

config.initialize()

from core import tree
from core import acl
from core import users
