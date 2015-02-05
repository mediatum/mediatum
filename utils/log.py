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
import inspect
import traceback


ROOT_STREAM_LOGFORMAT = '%(asctime)s [%(process)d/%(threadName)s] %(name)s %(levelname)s | %(message)s'
# this also logs filename and line number, which is great for debugging
# ROOT_STREAM_LOGFORMAT = '%(asctime)s %(name)s/%(module)s [%(threadName)s] %(levelname)s | %(message)s - %(pathname)s:%(lineno)d'
ROOT_FILE_LOGFORMAT = ROOT_STREAM_LOGFORMAT

# path's will be required in web/admin/modules/logfile.py
dlogfiles = {}


class ConsoleHandler(logging.StreamHandler):

    """A handler that logs to console in the sensible way.

    StreamHandler can log to *one of* sys.stdout or sys.stderr.

    It is more sensible to log to sys.stdout by default with only error
    (logging.ERROR and above) messages going to sys.stderr. This is how
    ConsoleHandler behaves.
    
    from: http://code.activestate.com/recipes/576819-logging-to-console-without-surprises/ 
    
    added: copy trace attribute to exc_text for TraceLogger support
    """

    def __init__(self):
        logging.StreamHandler.__init__(self)
        self.stream = None  # reset it; we are not going to use it anyway

    def emit(self, record):
        if hasattr(record, "trace"):
            record.exc_text = record.trace
            
        if record.levelno >= logging.ERROR:
            self.__emit(record, sys.stderr)
        else:
            self.__emit(record, sys.stdout)

    def __emit(self, record, strm):
        self.stream = strm
        logging.StreamHandler.emit(self, record)


class TraceLogger(logging.Logger):
        
    """Adds an optional traceback for some messages.
        
    A traceback is added if the logging level is at least `trace_level` 
    or requested in the logging call (if `trace` is a true value). 
    """
    
    _trace_level = logging.WARN 
    
    @property
    def trace_level(self, level):
        """All log messages above the given `level` will have an additional field with a stack trace up to the logging call
        """  
        self._trace_level = level
    
    def _log(self, level, msg, args, exc_info=None, extra=None, trace=None):
        """Adds an optional traceback for some messages and calls Logger._log.
        A traceback is added if the logging level is at least `trace_level` or requested in the logging call. 
        
        :param trace: Always add a trace if trace is true
        """
        if trace or (level >= self._trace_level and not exc_info):
            if extra is None:
                extra = {}
            f = inspect.currentframe()
            tblines = traceback.format_stack(f)
            
            # nice hack to shorten long and ugly athana handler stack traces ;)
            for start_lineno, line in enumerate(tblines):
                if ", in call_and_close" in line:
                    break
            else:
                start_lineno = 0
                
            # cut off calls in the logging module
            if "_showwarning" in tblines[-3]:
                end_lineno = -3
            else:
                end_lineno = -2
                
            tbtext = "".join(tblines[start_lineno:end_lineno])
            extra["trace"] = tbtext
            
        logging.Logger._log(self, level, msg, args, exc_info=exc_info, extra=extra)
        
    def makeRecord(self, name, level, fn, lno, msg, args, exc_info, func=None, extra=None):
        if exc_info:
            if extra is None:
                extra = {}
            
            # get additional info about the exception
            ex_type, ex, _ = exc_info     
            extra["exc_type"] = ex_type.__name__
            # add members of the exception as extra info except callables and non-public stuff
            for name, val in inspect.getmembers(ex, lambda a: not callable(a)):
                # overriding log message is not allowed, rename it
                if name == "message":
                    extra["exc_message"] = val
                # args just contains all exception args again, can be ignored
                elif not name.startswith("_") and name not in ("args",):
                    extra[name] = val
        
            if issubclass(ex_type, UnicodeError):
                obj = extra["object"]
                
                if isinstance(obj, str):
                    # escape string that caused this exception
                    start = extra["start"]
                    end = extra["end"]
                    snippet_start = start - 1000 if start > 1000 else start
                    snippet_end = end + 1000
                    
                    error_part = obj[start:end+1].encode("string_escape")
                    extra["object"] = obj[snippet_start:start-1] + "[ERROR]" + error_part + "[/ERROR]" + obj[end+1:snippet_end]
                else:
                    extra["object"] = obj[:2000]
        
        if extra and "lineno" in extra:
            del extra["lineno"]
        return logging.Logger.makeRecord(self, name, level, fn, lno, msg, args, exc_info, func=func, extra=extra)

### init
logging.setLoggerClass(TraceLogger)
logging.captureWarnings(True)

# get the logger after setting the logger class!
logg = logging.getLogger(__name__)


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
