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
import traceback
import re

# additional_handlers= []: logs only to own file; ['screen', 'everything']: logs to own file, stdout, everything.log
DEFAULT_ADDITIONAL_HANDLERS = []
DEFAULT_LOGLEVEL = logging.DEBUG
DEFAULT_LOGFORMAT = '%(asctime)s %(levelname)s %(message)s'


def cfg(logtype,
        additional_handlers=DEFAULT_ADDITIONAL_HANDLERS,
        logformat=DEFAULT_LOGFORMAT,
        loglevel=DEFAULT_LOGLEVEL):

    d = {}
    d['logtype'] = logtype
    d['additional_handlers'] = additional_handlers
    d['logformat'] = logformat
    d['loglevel'] = loglevel

    return [logtype, d]

LOGTYPES = [
    cfg("database"),
    cfg("backend"),
    cfg("frontend"),
    cfg("mediatumtal", ["screen"]),
    cfg("editor", loglevel=logging.DEBUG),
    cfg("usertracing", ["screen"]),
    cfg("athana", ["screen", "everything"]),
    cfg("errors", ["screen", "everything"]),
    cfg("services"),
    cfg("searchindex"),
    cfg("ftp", ["screen"]),
    cfg("oai"),
    cfg("z3950", ["screen"], logformat='%(asctime)s %(message)s'),
    cfg("workflows"),
]

# path's will be required in web/admin/modules/logfile.py
dlogfiles = {}


class PatternFilter(logging.Filter):

    def __init__(self, pattern):
        self.pattern = pattern

    def filter(self, record):
        return re.match(self.pattern, record.getMessage())


def initialize():
    log_screen = logging.getLogger('screen')
    l = logging.StreamHandler(sys.stdout)
    log_screen.handlers = []
    log_screen.addHandler(l)
    log_screen.setLevel(logging.DEBUG)

    log_everything = logging.getLogger('everything')
    log_everything.handlers = []

    filename = core.config.get('logging.file.everything', None)
    filepath = core.config.get('logging.path', None)
    if not filename and not filepath:
        filename = filepath = core.config.get('paths.tempdir')
        filename += 'everything.log'
        print 'Using temp directory (%s) for logging' % (filepath)
    if not filename and filepath:
        filename = filepath + 'everything.log'
    if not filepath and filename:
        filepath = filename[:filename.rfind("/") + 1]

    dlogfiles['everything'] = {'path': filepath, 'filename': filename}

    if filename:
        if not os.path.exists(filename[:filename.rfind("/") + 1]):
            os.mkdir(filename[:filename.rfind("/") + 1])
        l = logging.handlers.RotatingFileHandler(filename, maxBytes=33554432, backupCount=20)
        l.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
        log_everything.addHandler(l)

    # log_everything.addHandler(log_screen)
    log_everything.setLevel(logging.DEBUG)

    for name, cfgDict in LOGTYPES:
        log = logging.getLogger(name)
        log.handlers = []
        filename = core.config.get("logging.file." + name, None)
        if not filename and filepath:
            filename = filepath + name + '.log'

        if filename:
            if not os.path.exists(filename[:filename.rfind("/") + 1]):
                os.mkdir(filename[:filename.rfind("/") + 1])
            l = logging.handlers.RotatingFileHandler(filename, maxBytes=33554432, backupCount=20)
            l.setFormatter(logging.Formatter(cfgDict["logformat"]))
            log.addHandler(l)
            if "screen" in cfgDict["additional_handlers"]:
                log.addHandler(log_screen)
            if "everything" in cfgDict["additional_handlers"]:
                log.addHandler(log_everything)
            log.setLevel(cfgDict["loglevel"])

        dlogfiles[name] = {'path': filepath, 'filename': filename}

    logging.getLogger('backend').info('logging initialized (%s)' % (filepath))


def logException(message=""):
    errlog = logging.getLogger('errors')
    errlog.exception(message)


def addLogger(loggername, additional_handlers=["screen"], loglevel=logging.DEBUG):
    '''
    add new logger
    filename will be <loggername>.log
    additional_handlers may be a sublist of ["screen", "everything"]
    '''
    global cfg, LOGTYPES, dlogfiles

    if loggername in [lt[0] for lt in LOGTYPES]:
        logging.getLogger("backend").warning("tried to add logger for existing logger name %r" % loggername)
        return False

    filepath = core.config.get('logging.path', None)

    _cfgDict = cfg(loggername,
                   additional_handlers=additional_handlers,
                   loglevel=loglevel)

    cfgDict = _cfgDict[1]

    log = logging.getLogger(loggername)
    log.handlers = []
    filename = core.config.get("logging.file." + loggername, None)
    if not filename and filepath:
        filename = filepath + loggername + '.log'

    if filename:
        if not os.path.exists(filename[:filename.rfind("/") + 1]):
            os.mkdir(filename[:filename.rfind("/") + 1])

        l = logging.handlers.RotatingFileHandler(filename,
                                                 maxBytes=33554432,
                                                 backupCount=20)

        l.setFormatter(logging.Formatter(cfgDict["logformat"]))
        log.addHandler(l)
        if "screen" in cfgDict["additional_handlers"]:
            log_screen = logging.getLogger('screen')
            log.addHandler(log_screen)
        if "everything" in cfgDict["additional_handlers"]:
            log_everything = logging.getLogger('everything')
            log.addHandler(log_everything)
        log.setLevel(cfgDict["loglevel"])

        LOGTYPES.append(_cfgDict)

    dlogfiles[loggername] = {'path': filepath, 'filename': filename}
    logging.getLogger("backend").info("added logger %r" % loggername)
    return True
