# -*- coding: utf-8 -*-

# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import inspect
from decorator import decorator



class CaseMetaClass(type):
    """
    from http://hwiechers.blogspot.de/2010/08/case-classes-in-python.html
    """
    def __new__(mcs, name, bases, dict):
        def noop(self):
            pass

        for meth in ('__eq__', '__ne__', '__hash__', '__str__'):
            if meth in dict:
                raise Exception('{} must not be defined on class.' % (meth))

        if '__init__' in dict:
            args, varargs, varkw, _ = inspect.getargspec(dict['__init__'])
            if varkw is not None:
                raise Exception("__init__ can't take **kwargs")
            args = args[1:]
        else:
            args = []
            varargs = None

        if args and varargs:
            raise Exception("Case class __init__ can't have both args (other than self) and *args")

        for arg in args + ([varargs] if varargs else []):
            if arg.startswith('_'):
                raise Exception("Case class attributes can't start with '_'.")
            dict[arg] = property(lambda self, arg=arg: getattr(self, '_' + arg))

        def _init(func, self, *init_args) :
            setattr(self, '_CaseMetaClass__args', init_args)
            if varargs:
                setattr(self, '_' + varargs, init_args)
            else:
                for (name, value) in zip(args, init_args):
                    setattr(self, '_' + name, value)
        dict['__init__'] = decorator(_init, dict.get('__init__', noop))

        def str(self):
            values = [repr(x) for x in getattr(self,'_CaseMetaClass__args')]
            return name + '(' + ', '.join(values) + ')'
        dict['__str__'] = str
        dict['__repr__'] = str

        def eq(self, other):
            if other is None:
                return False
            if type(self) is not type(other):
                return False
            return self._CaseMetaClass__args == other._CaseMetaClass__args
        dict['__eq__'] = eq

        dict['__ne__'] = lambda self, other: not (self == other)
        dict['__hash__'] = lambda self: hash(type(self)) ^ hash(self._CaseMetaClass__args)

        return type.__new__(mcs, name, bases, dict)


class Case(object):
    __metaclass__ = CaseMetaClass
    @classmethod
    def tup(cls, args):
        return cls(*args)
