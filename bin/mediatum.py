#! /usr/bin/env nix-shell
#! nix-shell -i python

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


from __future__ import print_function


# This code patches a potential security risk in `urlparse.urlsplit`.
# ** It must be executed before any other modules are loaded **
# TODO This code can be dropped after an update to Python 2.7.17 .
def _patch_urlparse_urlsplit():
    from urlparse import urlsplit as _urlsplit_vulnerable
    def _urlsplit_patched(*args, **kwargs):
        rv = _urlsplit_vulnerable(*args, **kwargs)
        # Check netloc for unicode characters that decompose to any of '/?#@:'.
        # Those might lead further code astray, so we raise a ValueError.
        # See also https://bugs.python.org/issue36216 .
        # The following code is inspired by
        # https://github.com/python/cpython/commit/e37ef41289b77e0f0bb9a6aedb0360664c55bdd5 .
        from unicodedata import normalize
        if rv.netloc and isinstance(rv.netloc, unicode):
            normnetloc = normalize("NFKC", rv.netloc)
            if (rv.netloc!=normnetloc) and frozenset(normnetloc).intersection("/?#@:"):
                raise ValueError(
                    "invalid characters in netloc: {}".format(normnetloc))
        return rv
    import urlparse
    urlparse.urlsplit = _urlsplit_patched
_patch_urlparse_urlsplit()


from werkzeug._reloader import run_with_reloader
import configargparse
import tempfile
import os as _os
import sys as _sys
_sys.path.append(_os.path.abspath(_os.path.join(__file__, "..", "..")))
from core import config

SYSTEM_TMP_DIR = tempfile.gettempdir()


def stackdump_setup():
    import codecs
    import logging
    import sys
    logg = logging.getLogger(__name__)
    # stackdump

    import os
    import threading
    import traceback
    try:
        import IPython.core.ultratb as ultratb
    except:
        ultratb = None

    if ultratb is None:
        logg.warn("IPython not installed, stack dumps not available!")
    else:
        logg.info("IPython installed, write stack dumps to tmpdir with: `kill -QUIT <mediatum_pid>`")

        def dumpstacks(signal, frame):
            print("dumping stack")
            # we must use the system temp dir here because mediaTUM config must not be loaded here
            filepath = os.path.join(SYSTEM_TMP_DIR, "mediatum_threadstatus")
            id2name = dict([(th.ident, th.name) for th in threading.enumerate()])
            full = ["-" * 80]
            tb_formatter = ultratb.ListTB(color_scheme="Linux")
            for thread_id, stack in sys._current_frames().items():
                thread_name = id2name.get(thread_id, "")
                if not "Main" in thread_name:
                    stacktrace = traceback.extract_stack(stack)
                    stb = tb_formatter.structured_traceback(Exception, Exception(), stacktrace)[8:-1]
                    if stb:
                        formatted_trace = tb_formatter.stb2text(stb).strip()
                        with codecs.open("{}.{}".format(filepath, thread_id), "w", encoding='utf8') as wf:
                            wf.write("\n{}".format(formatted_trace))
                        if len(stb) > 4:
                            short_stb = stb[:2] + ["..."] + stb[-2:]
                        else:
                            short_stb = stb
                        formatted_trace_short = tb_formatter.stb2text(short_stb).strip()
                        full.append("# Thread: %s(%d)" % (thread_name, thread_id))
                        full.append(formatted_trace_short)
                        full.append("-" * 80)

            with codecs.open(filepath, "wf", encoding='utf8') as wf:
                wf.write("\n".join(full))

        import signal
        signal.signal(signal.SIGQUIT, dumpstacks)


def run(force_test_db=None, loglevel=None, automigrate=False):
    """Serve mediaTUM from the Athana HTTP Server and start FTP and Z3950, if requested"""
    # init.full_init() must be done as early as possible to init logging etc.
    from core import init
    init.full_init(force_test_db=force_test_db, root_loglevel=loglevel, automigrate=automigrate)

    from core.request_handler import request_finished as _request_finished
    @_request_finished
    def request_finished_db_session(*args):
        from core import db
        db.session.close()

    from core import app as flask_app
    return flask_app


def make_flask_app():
    parser = configargparse.ArgumentParser("mediaTUM start.py")

    parser.add_argument("-b", "--bind", default=None, help="hostname / IP to bind to, default: see config file")

    parser.add_argument("-p", "--http_port", default=None, help="HTTP port to use, default: see config file")

    parser.add_argument("-r", "--reload", action="store_true", default=False,
                        help="reload when code or config file changes, default false")

    parser.add_argument("-s", "--stackdump", action="store_true", default=True,
                        help="write stackdumps to temp dir {} on SIGQUIT, default true".format(SYSTEM_TMP_DIR))

    parser.add_argument("--force-test-db", action="store_true", default=False,
                        help="create / use database server with default database for testing (overrides configured db connection)")
    parser.add_argument("-l", "--loglevel", help="root loglevel, sensible values: DEBUG, INFO, WARN")
    parser.add_argument("-m", "--automigrate", action="store_true", default=False,
                        help="run automatic database schema upgrades on startup")

    args = parser.parse_args()
    print("start.py args:", args)

    def signal_handler_usr1(signum, stack):
        import utils.log
        utils.log.reopen_log(None, None)

    import signal
    signal.signal(signal.SIGUSR1, signal_handler_usr1)

    if args.stackdump:
        stackdump_setup()

    if args.reload:
        # don't use this in production!
        maybe_config_filepath = config.get_config_filepath()
        extra_files = [maybe_config_filepath] if maybe_config_filepath else []

        def main_wrapper():
            return run(args.force_test_db, args.loglevel, args.automigrate)

        return run_with_reloader(main_wrapper, extra_files)
    else:
        return run(args.force_test_db, args.loglevel, args.automigrate)


flask_app = make_flask_app()
# don't run mediaTUM server when this module is imported, unless FORCE_RUN is set
if __name__ == "__main__" or hasattr(__builtins__, "FORCE_RUN"):
    flask_app.run(config.get("host.name"), int(config.get("host.port")))
