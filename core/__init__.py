import os
import sys

editmodulepaths = [('', 'web/edit/modules')]

import utils.log

from core import config

config.initialize()

from core import acl
from core import users
# set by core.init.init_app()
db = None
app = None