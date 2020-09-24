import os as _os
import sys as _sys
_sys.path.append(_os.path.abspath(_os.path.join(_os.path.dirname(__file__), "..")))
import asyncore as _asyncore
import configargparse as _configargparse
import core.init as _core_init
import core.config as _core_config
import core.athana_z3950 as _core_athana_z3950
import utils.utils as _utils_utils


def run():
    parser = _configargparse.ArgumentParser("Z3950 start")
    parser.add_argument("-p", "--port", default=2021, help="port to use")
    parser.add_argument("--force-test-db", action="store_true", default=False,
                        help="create / use database server with default database for testing (overrides configured db connection)")
    parser.add_argument("-l", "--loglevel", help="root loglevel, sensible values: DEBUG, INFO, WARN")
    args = parser.parse_args()
    _core_init.full_init(force_test_db=args.force_test_db, root_loglevel=args.loglevel)

    with open(_core_config.get("paths.pidfile"), "wb") as f:
        f.write(str(_os.getpid()))

    _core_athana_z3950.z3950_server(port=args.port)
    while True:
        with _utils_utils.suppress(Exception, warn=False):
            _asyncore.loop(timeout=0.01)


if __name__ == "__main__":
    run()
