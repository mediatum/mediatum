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
from core import config
import logging
import sys
import logstash


ROOT_STREAM_LOGFORMAT = '%(asctime)s [%(process)d/%(threadName)s] %(name)s %(levelname)s | %(message)s'
# this also logs filename and line number, which is great for debugging
# ROOT_STREAM_LOGFORMAT = '%(asctime)s %(name)s/%(module)s [%(threadName)s] %(levelname)s | %(message)s - %(pathname)s:%(lineno)d'
ROOT_FILE_LOGFORMAT = ROOT_STREAM_LOGFORMAT

logg = logging.getLogger(__name__)

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
    levelname = config.get('logging.level', "DEBUG")
    try:
        level = getattr(logging, levelname.upper())
    except:
        print "unknown loglevel specified in logging config:", levelname
    root_logger.setLevel(level)

    stream_handler = ConsoleHandler()
    stream_handler.setFormatter(logging.Formatter(ROOT_STREAM_LOGFORMAT))
    root_logger.handlers = []
    root_logger.addHandler(stream_handler)
    
    
    logstash_handler = logstash.TCPLogstashHandler("localhost", 5959, version=1, message_type="mediatum")
    root_logger.addHandler(logstash_handler)


    filepath = config.get('logging.file', None)
        
    if filepath:
        dlogfiles['mediatum'] = {'path': filepath, 'filename': filepath}
        file_handler = logging.FileHandler(filepath) 
        file_handler.setFormatter(logging.Formatter(ROOT_FILE_LOGFORMAT))
        root_logger.addHandler(file_handler)
        logg.info('logging everything to %s', filepath)
