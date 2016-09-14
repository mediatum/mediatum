# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2016 by the mediaTUM authors
    :license: GPL3, see COPYING for details

    Provide wrappers for subprocess functions
    that allow to override the executable's name with a
    path given in the config file's section "external".
"""


from __future__ import absolute_import


import logging
import subprocess

import functools
import core.config


logg = logging.getLogger(__name__)


def _resolve_wrapper(fctn):
    """
    Return a new function that resembles the
    corresponding function from the subprocess module,
    but replace the executable's name with a
    value from the config file if listed there.
    Try with the 'executable' argument first,
    then with args[0] or (the single string) args.
    Don't change anything if "shell" is set True.
    """

    def resolve(name):
        """
        Actually looks in the config.
        """
        # Some modules can be called in their own process;
        # if such a module calls this one,
        # the config must be initialized again.
        # (inspired by similar code in parsepdf.py)
        if not core.config.settings:
            core.config.initialize()
        if not core.config.settings:
            logg.warn("cannot check executable name '%s' for replacement: failed to initialize config", name)
            return name
        if core.config.get("external.{}".format(name)):
            new_name = core.config.get("external.{}".format(name), name)
            logg.debug("resolved executable name '%s' to '%s'", name, new_name)
            return new_name
        return name

    @functools.wraps(fctn)
    def wrapper(args, **kwargs):
        if not kwargs.get("shell"):
            if kwargs.get("executable"):
                kwargs["executable"] = resolve(kwargs["executable"])
            elif isinstance(args, str):
                args = resolve(args)
            else:
                args = (resolve(args[0]),) + tuple(args[1:])
        return fctn(args, **kwargs)

    return wrapper


Popen = _resolve_wrapper(subprocess.Popen)
call = _resolve_wrapper(subprocess.call)
check_call = _resolve_wrapper(subprocess.check_call)
check_output = _resolve_wrapper(subprocess.check_output)
