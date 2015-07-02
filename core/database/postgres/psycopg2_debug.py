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
from psycopg2.extras import LoggingCursor
from werkzeug.datastructures import OrderedMultiDict

# used for SQL formatting, if present
try:
    import pygments
except ImportError:
    pygments = None


logg = logging.getLogger(__name__)

# logs SQL statements run by a psycopg2 logging connection
sql_log = logging.getLogger("sqllog")


class StatementHistory(object):

    """Keeps a history of SQL statements (optionally with time) and offers some pretty printing options.
    No precautions for thread safety.
    """

    def __init__(self, save_time=False):
        self._statements = OrderedMultiDict()
        self.save_time = save_time
        self.last_statement = None
        if save_time:
            self.append = self._append_with_time
        else:
            self.append = self._append

    def _append_with_time(self, stmt):
        self.last_statement = stmt 
        self._statements.add(stmt, time.time())
        
    def _append(self, stmt):
        self.last_statement = stmt 
        self._statements.add(stmt, 0)

    def clear(self):
        self._statements.clear()

    @property
    def statements(self):
        return self._statements.keys()
    
    @property
    def statements_with_time(self):
        return self._statements.items()
    

    def print_statements(self, show_time=None, highlight=True, pygments_style="native"):
        
        if show_time is None:
            show_time = self.save_time
        
        def format_stmt(stmt, timestamp):
            if show_time:
                return "{:.2f}: {}".format(timestamp, stmt)
            else:
                return stmt
        
        if highlight and pygments:
            from pygments.lexers import PostgresLexer
            from pygments.formatters import Terminal256Formatter
            lexer = PostgresLexer()
            formatter = Terminal256Formatter(style=pygments_style)

            def highlight_format_stmt(stmt, timestamp):
                return pygments.highlight(format_stmt(stmt, timestamp), lexer, formatter)
        
        else:
            highlight_format_stmt = format_stmt
            
        print()

        for stmt, timestamp in self._statements.items(multi=True):
            print(highlight_format_stmt(stmt, timestamp))


def make_debug_connection_factory(log_statement_trace=False, history_save_time=False):
    """Creates a DebugConnection which can be used as connection_factory for Psycopg2.connect()
    :param log_statement_trace: add trace to all SQL statement logs
    :param history_save_time: record unix time of execution in statement history
    """

    class DebugConnection(_connection):

        """Psycopg2 connection which keeps a history of SQL statements and logs them.
        Inspired by psycopg2.extras.LoggingConnection
        """

        def log(self, msg, curs):
            sql_log.debug(msg, trace=log_statement_trace)
            self._history.append(msg)

        def _check(self):
            if not hasattr(self, "_history"):
                self._history = StatementHistory(history_save_time)

        @property
        def history(self):
            self._check()
            return self._history

        def cursor(self, *args, **kwargs):
            self._check()
            kwargs.setdefault('cursor_factory', LoggingCursor)
            return super(DebugConnection, self).cursor(*args, **kwargs)

    return DebugConnection
