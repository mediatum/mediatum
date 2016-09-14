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
import datetime
import logging
import sys
import logstash
import inspect
import traceback
from logging import LogRecord

from core import config
from .date import format_date
import os
import hashlib
import random
import string

ROOT_STREAM_LOGFORMAT = '%(asctime)s [%(process)d/%(threadName)s] %(name)s %(levelname)s | %(message)s'
# this also logs filename and line number, which is great for debugging
# ROOT_STREAM_LOGFORMAT = '%(asctime)s %(name)s/%(module)s [%(threadName)s] %(levelname)s | %(message)s - %(pathname)s:%(lineno)d'
ROOT_FILE_LOGFORMAT = ROOT_STREAM_LOGFORMAT

# path's will be required in web/admin/modules/logfile.py
dlogfiles = {}


def tal_traceback_info():
    info = {}
    tal_traceback_line = None

    # hack for additional traceback info for TAL traces
    try:
        # XXX: this can fail with an index error, don't know why
        stack = inspect.stack()  # search for a python expr evaluation in the TAL interpreter stack trace
    except IndexError:
        return info, tal_traceback_line

    eval_frame_result = [f for f in stack if f[3] == "evaluate" and "talextracted" in f[1]]
    if eval_frame_result:

        eval_frame_locals = eval_frame_result[0][0].f_locals
        info["tal_expr"] = tal_expr = eval_frame_locals["expr"]
        tal_engine = eval_frame_locals["self"]
        if tal_engine.position:
            tal_lineno, tal_col = tal_engine.position
            info["tal_lineno"] = tal_lineno
            info["tal_col"] = tal_col
        else:
            tal_lineno = None
            tal_col = None
        # search for runTAL frame
        tal_frame_result = [f for f in stack if f[3] == "runTAL"]
        if tal_frame_result:
            tal_call_locals = tal_frame_result[0][0].f_locals
            info["tal_filename"] = tal_filename = tal_call_locals["file"]
            info["tal_macro"] = tal_macro = tal_call_locals["macro"]
        # format a line that looks like a traceback line
        # this produces a clickable link in Pycharm or Eclipse, for example ;)
            if tal_filename:
                tal_filepath = os.path.join(config.basedir, tal_filename)
            else:
                tal_filepath = "<string>"  # no filename? template was rendered from a string
            tal_traceback_line = u'\n  File "{}", line {}, in {}\n    {}'.format(tal_filepath,
                                                                                 tal_lineno,
                                                                                 tal_macro or "<template>",
                                                                                 tal_expr)

    return info, tal_traceback_line


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

    # All log messages above the given `level` will have an additional field with a stack trace up to the logging call
    trace_level = logging.WARN

    # omit stack trace lines before these token have been found
    start_trace_at = (", in call_and_close", )

    # omit stack trace lines after these token have been found
    stop_trace_at = ("/sqlalchemy/", )

    # skip lines in the strack trace
    # the tuple may contain strings or callables which are called with a single line as argument, returning bool
    skip_trace_lines = (lambda l: "tal" in l and not ("TAL" in l or "evaluate" in l), )

    def __init__(self, *params):
        super(TraceLogger, self).__init__(*params)
        # activate special debugging code for TAL templates, will be set later when config is avaiable
        self.use_tal_extension = None

    def _log(self, level, msg, args, exc_info=None, extra=None, trace=None):
        """Adds an optional traceback for some messages and calls Logger._log.
        A traceback is added if the logging level is at least `trace_level` or requested in the logging call.

        :param trace: Always add trace if true, never add one if false. Use trace_level if None. Defaults to None.
        """
        if trace or (trace is None and level >= self.trace_level and not exc_info):
            if extra is None:
                extra = {}
            frame = inspect.currentframe()
            tblines = traceback.format_stack(frame)

            def find_start_lineno():
                # nice hack to shorten long and ugly stack traces ;)
                # TODO: support callables
                for start_lineno, line in enumerate(tblines):
                    for text in self.start_trace_at:
                        if text in line:
                            return start_lineno + 1, text
                else:
                    return 0, None

            def find_end_lineno():
                for end_lineno, line in enumerate(tblines):
                    for text in self.stop_trace_at:
                        if text in line:
                            return end_lineno, text
                else:
                    # cut off calls in the logging module
                    if "_showwarning" in tblines[-3]:
                        return -3, None
                    else:
                        return -2, None

            start_lineno, start_cutoff = find_start_lineno()
            end_lineno, end_cutoff = find_end_lineno()
            lines_cut = tblines[start_lineno:end_lineno]

            def skip_line(line):
                for skip in self.skip_trace_lines:
                    if callable(skip):
                        if skip(line):
                            return True

                    elif skip in line:
                        return True

                return False

            lines_without_skipped = [l for l in lines_cut if not skip_line(l)]
            num_skipped_lines = len(lines_cut) - len(lines_without_skipped)

            # now, let's start building our customized strack trace
            final_tracelines = []

            if start_cutoff:
                final_tracelines.append("[... omitting lines up to '{}']\n".format(start_cutoff))

            final_tracelines.extend(lines_without_skipped)

            if num_skipped_lines:
                final_tracelines.append("[filtered {} lines]".format(num_skipped_lines))

            if end_cutoff:
                final_tracelines.append("[omitting lines starting at '{}' ...]".format(end_cutoff))

            extra["trace"] = "".join(final_tracelines)

            if self.use_tal_extension is None and config.settings is not None:
                self.use_tal_extension = config.getboolean("logging.tal_extension", True)

            if self.use_tal_extension:
                tal_info, maybe_tal_traceback_line = tal_traceback_info()
                extra.update(tal_info)
                if maybe_tal_traceback_line:
                    extra["trace"] += maybe_tal_traceback_line

        logging.Logger._log(self, level, msg, args, exc_info=exc_info, extra=extra)

    def makeRecord(self, name, level, fn, lno, msg, args, exc_info, func=None, extra=None):
        record = LogRecord(name, level, fn, lno, msg, args, exc_info, func)
        if exc_info:
            if extra is None:
                extra = {}
            # get additional info about the exception
            ex_type, ex, _ = exc_info
            extra["exc_type"] = ex_type.__name__
            # add members of the exception as extra info except callables and non-public stuff
            for name, val in inspect.getmembers(ex, lambda a: not callable(a)):
                # args just contains all exception args again, can be ignored
                if not name.startswith("_") and name not in ("args",):
                    # rename keys which collide with names from the log record
                    if name in ["message", "asctime"] or hasattr(record, name):
                        extra["exc_" + name] = val
                    else:
                        extra[name] = val

            if issubclass(ex_type, UnicodeError):
                obj = extra["object"]

                if isinstance(obj, str):
                    # escape string that caused this exception
                    start = extra["start"]
                    end = extra["end"]
                    snippet_start = start - 1000 if start > 1000 else start
                    snippet_end = end + 1000

                    error_part = obj[start:end + 1].encode("string_escape")
                    extra["object"] = obj[snippet_start:start - 1] + "[ERROR]" + error_part + "[/ERROR]" + obj[end + 1:snippet_end]
                else:
                    extra["object"] = obj[:2000]

        if extra is not None:
            for key in extra:
                if (key in ["message", "asctime"]) or (key in record.__dict__):
                    raise KeyError("Attempt to overwrite %r in LogRecord" % key)
                record.__dict__[key] = extra[key]

        return record

# init
logging.setLoggerClass(TraceLogger)
logging.captureWarnings(True)

# get the logger after setting the logger class!
logg = logging.getLogger(__name__)


def initialize(level=None, log_filepath=None, log_filename=None, use_logstash=None):
    root_logger = logging.getLogger()

    if level is None:
        levelname = config.get('logging.level', "INFO")
        try:
            level = getattr(logging, levelname.upper())
        except:
            print "unknown loglevel specified in logging config:", levelname

    root_logger.setLevel(level)
    stream_handler = ConsoleHandler()
    stream_handler.setFormatter(logging.Formatter(ROOT_STREAM_LOGFORMAT))
    root_logger.handlers = []
    root_logger.addHandler(stream_handler)

    if use_logstash is None:
        use_logstash = config.get('logging.use_logstash', "true") == "true"

    if use_logstash:
        logstash_handler = logstash.TCPLogstashHandler("localhost", 5959, version=1, message_type="mediatum")
        root_logger.addHandler(logstash_handler)

    if log_filepath is None:
        log_filepath = config.get('logging.file', None)
        
    if log_filepath is None:
        log_dir = config.get("logging.dir", None) 
        if log_dir:
            if not log_filename:
                # use name of start script as log file name
                log_filename = os.path.basename(os.path.splitext(sys.argv[0])[0]) + ".log"

            log_filepath = os.path.join(log_dir, log_filename)

    if log_filepath:
        dlogfiles['mediatum'] = {'path': log_filepath, 'filename': log_filepath}
        file_handler = logging.FileHandler(log_filepath)
        file_handler.setFormatter(logging.Formatter(ROOT_FILE_LOGFORMAT))
        root_logger.addHandler(file_handler)
        logg.info('--- logging everything to %s ---', log_filepath)


def make_xid_and_errormsg_hash():
    """Builds a unique string (exception ID) that may be exposed to the user without revealing to much.
    Added to the logging of an event should make it easier to relate.

    :param errormsg: str
    """
    # : and - interferes with elasticsearch query syntax, better use underscores in the datetime string
    date_now = datetime.datetime.now().strftime("%Y_%m_%dT%H_%M_%S")
    error_msg = str(sys.exc_info()[1])
    formatted_traceback = "\n".join(traceback.format_tb(sys.exc_info()[2]))
    hashed_errormsg = hashlib.md5(error_msg).hexdigest()[:6]
    hashed_tb = hashlib.md5(formatted_traceback).hexdigest()[:6]
    # http://stackoverflow.com/questions/2257441/random-string-generation-with-upper-case-letters-and-digits
    random_string = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(4))
    xid = "%s__%s__%s__%s" % (date_now, hashed_tb, hashed_errormsg, random_string)
    return xid, hashed_errormsg, hashed_tb


def extra_log_info_from_req(req, add_user_info=True):

    extra = {"args": dict(req.args),
             "path": req.path,
             "method": req.method}

    if req.method == "POST":
        extra["form"] = dict(req.form)
        extra["files"] = [{"filename": f.filename,
                           "tempname": f.tempname,
                           "content_type": f.content_type,
                           "filesize": f.filesize} for f in req.files.values()]

    if add_user_info:
        from core.users import user_from_session
        user = user_from_session(req.session)
        extra["user_is_anonymous"] = user.is_anonymous

        if not user.is_anonymous:
            extra["user_id"] = user.id
            extra["user_is_editor"] = user.is_editor
            extra["user_is_admin"] = user.is_admin

        extra["headers"] = {k.lower(): v for k, v in [h.split(": ", 1) for h in req.header]}

    return extra
