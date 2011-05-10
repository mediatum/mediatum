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
import os
import core.config
import logging
import logging.handlers
import sys
import traceback

LOGTYPES = ["database","backend","frontend","editor","usertracing","athana","errors","services","searchindex"]

def initialize():
    log_screen = logging.getLogger('screen')
    l = logging.StreamHandler(sys.stdout)
    log_screen.handlers = []
    log_screen.addHandler(l)
    log_screen.setLevel(logging.INFO)

    log_everything = logging.getLogger('everything')
    log_everything.handlers = []

    filename = core.config.get('logging.file.everything', None)
    filepath = core.config.get('logging.path', None)
    if not filename and not filepath:
        filename = filepath = core.config.get('paths.tempdir')
        filename += 'everything.log'
        print 'Using temp directory (%s) for logging' %(filepath)
    if not filename and filepath:
        filename = filepath + 'everything.log'
    if not filepath and filename:
        filepath = filename[:filename.rfind("/")+1]
    
    if filename:
        if not os.path.exists(filename[:filename.rfind("/")+1]):
            os.mkdir(filename[:filename.rfind("/")+1])
        l = logging.handlers.RotatingFileHandler(filename, maxBytes=33554432, backupCount=20)
        l.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
        log_everything.addHandler(l)

    log_everything.addHandler(log_screen)
    log_everything.setLevel(logging.DEBUG)

    for name in LOGTYPES:
        log = logging.getLogger(name)
        log.handlers = []
        filename = core.config.get("logging.file."+name, None)
        if not filename and filepath:
            filename = filepath + name + '.log'

        if filename:
            if not os.path.exists(filename[:filename.rfind("/")+1]):
                os.mkdir(filename[:filename.rfind("/")+1])
            l = logging.handlers.RotatingFileHandler(filename, maxBytes=33554432, backupCount=20)
            l.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
            log.addHandler(l)
            log.addHandler(log_everything)
            log.setLevel(logging.DEBUG)

    logging.getLogger('backend').info('logging initialized (%s)' %(filepath))

    
def logException(message=None):
    errlog = logging.getLogger('errors')
    class Errorprint:
        def write (self, message):
            errlog.error(message.rstrip())
    if(message):
        errlog.error(message)
    errlog.error(str(sys.exc_info()[0]) + " " + str(sys.exc_info()[1]))
    traceback.print_tb(sys.exc_info()[2],None,Errorprint())
