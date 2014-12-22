"""
 mediatum - a multimedia content repository

 Copyright (C) 2007 Arne Seifert <seiferta@in.tum.de>
 Copyright (C) 2007 Matthias Kramm <kramm@in.tum.de>
 Copyright (C) 2011 Werner Neudenberger <neudenberger@ub.tum.de>

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
import core.config
import logging
import logging.handlers
import sys


DEFAULT_LOGLEVEL = logging.DEBUG
# use for special file loggers defined in LOGTYPES
DEFAULT_LOGFORMAT = '%(asctime)s %(levelname)s %(message)s'
# used for the root logger
ROOT_STREAM_LOGFORMAT = '%(asctime)s [%(process)d/%(threadName)s] %(name)s/%(module)s %(levelname)s | %(message)s'
# this also logs filename and line number, which is great for debugging
# ROOT_STREAM_LOGFORMAT = '%(asctime)s %(name)s/%(module)s [%(threadName)s] %(levelname)s | %(message)s - %(pathname)s:%(lineno)d'
ROOT_FILE_LOGFORMAT = ROOT_STREAM_LOGFORMAT

logg = logging.getLogger(__name__)


def cfg(logtype, logformat=None, loglevel=None):
    d = {}
    d['logtype'] = logtype
    d['logformat'] = logformat or DEFAULT_LOGFORMAT
    d['loglevel'] = loglevel or DEFAULT_LOGLEVEL

    return [logtype, d]

LOGTYPES = [
    cfg("database"),
    cfg("backend"),
    cfg("frontend"),
    cfg("mediatumtal"),
    cfg("editor", loglevel=logging.INFO),
    cfg("usertracing"),
    cfg("athana", loglevel=logging.INFO),
    cfg("errors"),
    cfg("services"),
    cfg("searchindex"),
    cfg("ftp"),
    cfg("oai"),
    cfg("z3950", logformat='%(asctime)s %(message)s'),
    cfg("workflows"),
]

# path's will be required in web/admin/modules/logfile.py
dlogfiles = {}


class ConsoleHandler(logging.StreamHandler):

    """A handler that logs to console in the sensible way.

    StreamHandler can log to *one of* sys.stdout or sys.stderr.

    It is more sensible to log to sys.stdout by default with only error
    (logging.ERROR and above) messages going to sys.stderr. This is how
    ConsoleHandler behaves.
    
    from: http://code.activestate.com/recipes/576819-logging-to-console-without-surprises/ 
    """

    def __init__(self):
        logging.StreamHandler.__init__(self)
        self.stream = None  # reset it; we are not going to use it anyway

    def emit(self, record):
        if record.levelno >= logging.ERROR:
            self.__emit(record, sys.stderr)
        else:
            self.__emit(record, sys.stdout)

    def __emit(self, record, strm):
        self.stream = strm
        logging.StreamHandler.emit(self, record)


def initialize():
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    stream_handler = ConsoleHandler()
    stream_handler.setFormatter(logging.Formatter(ROOT_STREAM_LOGFORMAT))
    root_logger.handlers = []
    root_logger.addHandler(stream_handler)

    filename = core.config.get('logging.file.everything', None)
    filepath = core.config.get('logging.path', None)
    if not filename and not filepath:
        filename = filepath = core.config.get('paths.tempdir')
        filename += 'everything.log'
        logg.info('Using temp directory (%s) for logging', filepath)
    if not filename and filepath:
        filename = filepath + 'everything.log'
    if not filepath and filename:
        filepath = filename[:filename.rfind("/") + 1]

    dlogfiles['everything'] = {'path': filepath, 'filename': filename}

    if filename:
        if not os.path.exists(filename[:filename.rfind("/") + 1]):
            os.mkdir(filename[:filename.rfind("/") + 1])
        file_handler = logging.handlers.RotatingFileHandler(filename, maxBytes=33554432, backupCount=20)
        file_handler.setFormatter(logging.Formatter(ROOT_FILE_LOGFORMAT))
        root_logger.addHandler(file_handler)
        logg.info('logging everything to %s', filepath)

    for name, cfgDict in LOGTYPES:
        log = logging.getLogger(name)
        log.handlers = []
        filename = core.config.get("logging.file." + name, None)
        if not filename and filepath:
            filename = filepath + name + '.log'

        if not os.path.exists(filename[:filename.rfind("/") + 1]):
            os.mkdir(filename[:filename.rfind("/") + 1])
        l = logging.handlers.RotatingFileHandler(filename, maxBytes=33554432, backupCount=20)
        l.setFormatter(logging.Formatter(cfgDict["logformat"]))
        log.addHandler(l)
        log.setLevel(cfgDict["loglevel"])

        dlogfiles[name] = {'path': filepath, 'filename': filename}
        logg.info("added logger %s, file %s", name, filename)


def logException(message=None):
    errlog = logging.getLogger('errors')
    errlog.exception(message or "")


def addLogger(loggername, additional_handlers=None, loglevel=None, logformat=None):
    '''
    add new logger
    filename will be <loggername>.log
    '''
    global cfg, LOGTYPES, dlogfiles

    if loggername in [lt[0] for lt in LOGTYPES]:
        logg.warn("tried to add logger for existing logger name %r", loggername)
        return False

    filepath = core.config.get('logging.path', None)

    _cfgDict = cfg(loggername,
                   logformat=logformat,
                   loglevel=loglevel)

    cfgDict = _cfgDict[1]

    logger = logging.getLogger(loggername)
    logger.handlers = []
    filename = core.config.get("logging.file." + loggername, None)
    if not filename and filepath:
        filename = filepath + loggername + '.log'

    if filename:
        if not os.path.exists(filename[:filename.rfind("/") + 1]):
            os.mkdir(filename[:filename.rfind("/") + 1])

        file_handler = logging.handlers.RotatingFileHandler(filename,
                                                            maxBytes=33554432,
                                                            backupCount=20)

        file_handler.setFormatter(logging.Formatter(cfgDict["logformat"]))
        file_handler.setLevel(cfgDict["loglevel"])
        logger.addHandler(file_handler)

        LOGTYPES.append(_cfgDict)

    dlogfiles[loggername] = {'path': filepath, 'filename': filename}
    return True
