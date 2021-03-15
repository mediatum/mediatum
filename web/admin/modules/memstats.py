"""
 mediatum - a multimedia content repository

 Copyright (C) 2007 Arne Seifert <seiferta@in.tum.de>
 Copyright (C) 2007 Matthias Kramm <kramm@in.tum.de>

 This program is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.

 This program is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
from __future__ import division

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
