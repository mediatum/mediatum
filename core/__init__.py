import os
import sys

editmodulepaths = [('', 'web/edit/modules')]

from core import config

config.initialize()

from core import tree
from core import acl
from core import users
