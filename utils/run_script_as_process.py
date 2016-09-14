"""
 mediatum - a multimedia content repository

 Copyright (C) 2007 Arne Seifert <seiferta@in.tum.de>
 Copyright (C) 2007 Matthias Kramm <kramm@in.tum.de>
 Copyright (C) 2012 Werner Neudenberger <neudenberger@ub.tum.de>

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

import os
import platform
import sys
import multiprocessing
import subprocess


def detach(program, *args):
    """
    Caution: In contrast to most other code of mediatum,
    this function does *not* resolve the executable's name
    with the config "external" section (c.f. utils.process).
    """
    return subprocess.Popen([program] + list(args))


def run():

    script_path = (os.getcwd() + "/" + sys.argv[1].replace(os.getcwd(), "")).replace("\\", "/").replace("//", "/").replace("//", "/")

    p = multiprocessing.Process(target=detach, args=[sys.executable, script_path] + sys.argv[2:])
    p.start()

if __name__ == '__main__':
    run()
