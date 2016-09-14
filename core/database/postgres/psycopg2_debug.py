# -*- coding: utf-8 -*-
"""

    Some debugging extensions for Psycopg2, our database driver

    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from __future__ import print_function
import logging
import time
from psycopg2.extensions import connection as _connection
from psycopg2.extensions import cursor as _cursor
from werkzeug.datastructures import OrderedMultiDict
from decorator import contextmanager
from utils.compat import iteritems

# used for SQL formatting, if present
try:
    import pygments
except ImportError:
    pygments = None


DEFAULT_PYGMENTS_STYLE = "native"

logg = logging.getLogger(__name__)

# logs SQL statements run by a psycopg2 logging connection
sql_log = logging.getLogger("sqllog")


def _make_statement_formatter(show_time, highlight, pygments_style, formatter_cls=None):

    def format_stmt(stmt, timestamp=0, duration=0):
        if show_time:
            return "{:.2f} ({:.2f}ms): {}".format(timestamp, duration * 1000, stmt.strip())
        else:
            return stmt

    if highlight and pygments:
        from pygments.lexers import PostgresLexer
        lexer = PostgresLexer()

        if formatter_cls is None:
            from pygments.formatters import Terminal256Formatter
            formatter_cls = Terminal256Formatter
            
        formatter = formatter_cls(style=pygments_style)
        
        def highlight_format_stmt(stmt, timestamp=0, duration=0):
            return pygments.highlight(format_stmt(stmt, timestamp, duration), lexer, formatter)

        return highlight_format_stmt
    else:
        return format_stmt


class StatementHistory(object):

    """Keeps a history of SQL statements with execution time and offers some pretty printing options.
    No precautions for thread safety.
    """

    def __init__(self):
        self._reset()

    def _reset(self):
        self._statements = OrderedMultiDict()
        self.last_statement = None
        self.last_duration = None
        self.last_timestamp = None

    def append(self, stmt, timestamp, duration, notices):
        self.last_statement = stmt
        self.last_timestamp = timestamp
        self.last_duration = duration
        self.last_notices = notices
        self._statements.add(stmt, (timestamp, duration, notices))

    def clear(self):
        # clear() does not work on OrderedMultiDict, bug in werkzeug?
        self._reset()

    @property
    def statements(self):
        return self._statements.keys()

    @property
    def statements_with_all_infos(self):
        return iteritems(self._statements)
    
    @property
    def statements_with_time(self):
        return ((k, v[0]) for k, v in iteritems(self._statements))

    def format_statement(self, stmt, highlight=True, time=0, duration=0, pygments_style=DEFAULT_PYGMENTS_STYLE, formatter_cls=None):
        show_time = time and duration
        highlight_format_stmt = _make_statement_formatter(show_time, highlight, pygments_style, formatter_cls)
        return highlight_format_stmt(stmt)

    def print_last_statement(self, show_time=True, highlight=True, pygments_style=DEFAULT_PYGMENTS_STYLE):
        if self.last_statement is None:
            print("history is empty")
            return

        highlight_format_stmt = _make_statement_formatter(show_time, highlight, pygments_style)
        print()
        print(highlight_format_stmt(self.last_statement, self.last_timestamp, self.last_duration))

    def print_statements(self, show_time=True, highlight=True, pygments_style=DEFAULT_PYGMENTS_STYLE):
        if self.last_statement is None:
            print("history is empty")
            return

        highlight_format_stmt = _make_statement_formatter(show_time, highlight, pygments_style)
        print()

        for stmt, (timestamp, duration) in self._statements.items(multi=True):
            print(highlight_format_stmt(stmt, timestamp, duration))


class DebugCursor(_cursor):

    """A cursor that logs queries with execution timestamp and duration,
    using its connection logging facilities.
    """

    @contextmanager
    def _logging(self):
        start_ts = time.time()
        yield
        end_ts = time.time()
        duration = end_ts - start_ts
        self.connection.log(self.query, end_ts, duration, self)

    def execute(self, query, vars=None):
        with self._logging():
            return super(DebugCursor, self).execute(query, vars)

    def callproc(self, procname, vars=None):
        with self._logging():
            return super(DebugCursor, self).callproc(procname, vars)


def make_debug_connection_factory(log_statement_trace=False):
    """Creates a DebugConnection which can be used as connection_factory for Psycopg2.connect()
    :param log_statement_trace: add trace to all SQL statement logs
    """

    class DebugConnection(_connection):

        """Psycopg2 connection which keeps a history of SQL statements and logs them.
        Inspired by psycopg2.extras.LoggingConnection
        """

        def log(self, msg, timestamp, duration, curs):
            notices = [notice.strip() for notice in self.notices]
            msg_with_duration = "%.2fms: " % (duration * 1000) + msg
            sql_log.debug(msg_with_duration, trace=log_statement_trace, 
                          extra={"duration": duration, "timestamp": timestamp, "notices": notices})
            self._history.append(msg, timestamp, duration, notices)

        def _check(self):
            if not hasattr(self, "_history"):
                self._history = StatementHistory()

        @property
        def history(self):
            self._check()
            return self._history

        def cursor(self, *args, **kwargs):
            self._check()
            kwargs.setdefault('cursor_factory', DebugCursor)
            return super(DebugConnection, self).cursor(*args, **kwargs)

    return DebugConnection
