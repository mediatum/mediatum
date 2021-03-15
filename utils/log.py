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
from __future__ import division

import datetime
import logging
import logging.handlers as _logging_handlers
import sys
import traceback

from core import config
from .date import format_date
import hashlib
import string
try:
    import uwsgi as _uwsgi
except ImportError:
    _uwsgi = None
import utils as _utils_utils

ROOT_STREAM_LOGFORMAT = '%(asctime)s [%(process)d/%(threadName)s] %(name)s %(levelname)s | %(message)s'
# this also logs filename and line number, which is great for debugging
# ROOT_STREAM_LOGFORMAT = '%(asctime)s %(name)s/%(module)s [%(threadName)s] %(levelname)s | %(message)s - %(pathname)s:%(lineno)d'
ROOT_FILE_LOGFORMAT = ROOT_STREAM_LOGFORMAT

# init
logging.captureWarnings(True)

# get the logger after setting the logger class!
logg = logging.getLogger(__name__)


def initialize(level=None, log_filepath=None):
    root_logger = logging.getLogger()

    if level is None:
        level = int(logging.getLevelName(config.get("logging.level", "info").upper()))

    root_logger.setLevel(level)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging.Formatter(ROOT_STREAM_LOGFORMAT))
    root_logger.handlers = []
    root_logger.addHandler(stream_handler)

    if _uwsgi:
        return

    if log_filepath is None:
        log_filepath = config.get('logging.file', None)

    if log_filepath:
        file_handler = _logging_handlers.WatchedFileHandler(log_filepath)
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
    random_string = _utils_utils.gen_secure_token(64).upper()
    xid = "%s__%s__%s__%s" % (date_now, hashed_tb, hashed_errormsg, random_string)
    return xid, hashed_errormsg, hashed_tb
