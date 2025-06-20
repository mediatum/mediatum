#! /usr/bin/env python2

# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import configargparse
import logging as _logging
import os as _os
import sys as _sys
import tempfile

_sys.path.append(_os.path.abspath(_os.path.join(__file__, "..", "..")))

from werkzeug._reloader import run_with_reloader

import core as _core
import core.init as _
from core import config

_logg = _logging.getLogger(__name__)

SYSTEM_TMP_DIR = tempfile.gettempdir()


def run(loglevel=None, automigrate=False):
    """Serve mediaTUM from the WSGI Server Flask, if requested"""
    # init.full_init() must be done as early as possible to init logging etc.
    _core.init.full_init(root_loglevel=loglevel, automigrate=automigrate)
    return _core.app


def make_flask_app():
    parser = configargparse.ArgumentParser("mediaTUM start.py")

    parser.add_argument("-b", "--bind", default=None, help="hostname / IP to bind to, default: see config file")

    parser.add_argument("-p", "--http_port", default=None, help="HTTP port to use, default: see config file")

    parser.add_argument("-r", "--reload", action="store_true", default=False,
                        help="reload when code or config file changes, default false")

    parser.add_argument("-l", "--loglevel", help="root loglevel, sensible values: DEBUG, INFO, WARN")
    parser.add_argument("-m", "--automigrate", action="store_true", default=False,
                        help="run automatic database schema upgrades on startup")

    args = parser.parse_args()
    _logg.debug("start.py args: %s", args)

    if args.reload:
        # don't use this in production!
        maybe_config_filepath = config.get_config_filepath()
        extra_files = [maybe_config_filepath] if maybe_config_filepath else []

        def main_wrapper():
            return run(args.loglevel, args.automigrate)

        return run_with_reloader(main_wrapper, extra_files)
    else:
        return run(args.loglevel, args.automigrate)


flask_app = make_flask_app()
# don't run mediaTUM server when this module is imported, unless FORCE_RUN is set
if __name__ == "__main__" or hasattr(__builtins__, "FORCE_RUN"):
    flask_app.run()
