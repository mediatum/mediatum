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
from werkzeug._reloader import run_with_reloader
import configargparse
import tempfile
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


def main(host=None, http_port=None, redis_sessions=False, force_test_db=None):
    """Serve mediaTUM from the Athana HTTP Server and start FTP and Z3950, if requested"""
    # init.full_init() must be done as early as possible to init logging etc.
    from core import init
    init.full_init(force_test_db=force_test_db)

    # init all web components
    from core import webconfig
    from core import athana
    webconfig.initContexts()

    @athana.request_finished
    def request_finished_db_session(*args):
        from core import db
        db.session.close()

    # scheduler thread
    # import core.schedules
    # try:
    #     core.schedules.startThread()
    # except:
    #     logg.exception("Error starting scheduler thread")

    # start main web server, Z.39.50 and FTP, if configured
    if config.get('z3950.activate', '').lower() == 'true':
        z3950port = int(config.get("z3950.port", "2021"))
    else:
        z3950port = None

    athana.setThreads(int(config.get("host.threads", "8")))
    if redis_sessions:
        print("WARNING: using experimental persistent redis session support, only for testing!!!")
        athana.USE_PERSISTENT_SESSIONS = True

    import datetime
    with open("/tmp/mediatum.started", "w") as wf:
        wf.write(datetime.datetime.now().isoformat())
        wf.write("\n")

    athana.run(host or config.get("host.host", "0.0.0.0"), http_port or int(config.get("host.port", "8081")), z3950port)


if __name__ == "__main__":
    parser = configargparse.ArgumentParser("mediaTUM start.py")

    parser.add_argument("-b", "--bind", default=None, help="hostname / IP to bind to, default: see config file")

    parser.add_argument("-p", "--http_port", action="store_true", default=None, help="HTTP port to use, default: see config file")

    parser.add_argument("-r", "--reload", action="store_true", default=False,
                        help="reload when code or config file changes, default false")

    parser.add_argument("-s", "--stackdump", action="store_true", default=True,
                        help="write stackdumps to temp dir {} on SIGQUIT, default true".format(SYSTEM_TMP_DIR))

    parser.add_argument("--force-test-db", action="store_true", default=False,
                        help="create / use test database server and test database (overrides configured db connection)")
    parser.add_argument(
        "--redis-sessions",
        action="store_true",
        default=False,
        help="EXPERIMENTAL: save sessions to redis, making them persistent, requires redis-collections and a redis server on localhost!")

    args = parser.parse_args()
    print("start.py args:", args)

    if args.stackdump:
        stackdump_setup()

    if args.reload:
        # don't use this in production!
        extra_files = [config.get_config_filepath()]

        def main_wrapper():
            main(args.bind, args.http_port, args.redis_sessions, args.force_test_db)
        run_with_reloader(main_wrapper, extra_files)
    else:
        main(args.bind, args.http_port, args.redis_sessions, args.force_test_db)
