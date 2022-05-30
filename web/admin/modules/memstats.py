# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

try:
    import pympler
    from pympler.asizeof import asizeof
    from pympler import summary
    from pympler import muppy
except:
    pympler = None
import humanize

import gc
from itertools import islice
from web.admin.adminutils import getAdminStdVars
from core.templating import make_template_functions
from contenttypes import data
from utils.compat import iteritems


render_template, render_macro = make_template_functions("web/admin/modules")


def getInformation():
    return{"version":"1.0"}

def validate(req, op):
    return view(req, op)


def view(req, op):
    all_objects = gc.get_objects()

    memory_info = {
        "count": len(all_objects),
        "total_size": 0,
        "summary": ""
    }

    sessions_info = {
        "count": 1,
        "total_size": 0,
        "summary": ""
    }

    if pympler:
        sessions_info["total_size"] = 1
        summarized_all_objects = sorted(summary.summarize(all_objects), key=lambda t: t[2], reverse=True)
        memory_info["summary"] = summarized_all_objects[:500]

    import os
    if "MEDIATUM_EMBED_IPYTHON" in os.environ:
        import IPython
        IPython.embed()

    del all_objects

    return render_template("memstats.j2.jade",
                           sessions=sessions_info,
                           memory=memory_info,
                           naturalsize=humanize.filesize.naturalsize)
