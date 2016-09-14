# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2016 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""


import errno
import os

import pytest

import core.config
import utils.process


echo_str = "bnjqHETiqqEZu2"
executable = "SXEs4wXUtVPvm9"
arg1echo = "X-{0}-{0}-Y".format  # replicates the shell script
settings_external = {
    "external.{}".format(executable): os.path.join(os.path.dirname(__file__), "test_process_arg1echo.sh"),
    "external.cat": "missing_executable_file_Y2TyGsm75sQrhb",
}


def test_Popen_redirect(monkeypatch):
    monkeypatch.setattr(core.config, "settings", settings_external)
    utils.process.Popen((executable,)).communicate()


def test_call_redirect(monkeypatch):
    monkeypatch.setattr(core.config, "settings", settings_external)
    output = utils.process.call((executable,))


def test_check_call_redirect(monkeypatch):
    monkeypatch.setattr(core.config, "settings", settings_external)
    utils.process.check_call((executable,))


def test_check_output_redirect(monkeypatch):
    monkeypatch.setattr(core.config, "settings", settings_external)
    output = utils.process.check_output((executable, echo_str))
    assert output == arg1echo(echo_str)


def test_check_output_noredirect(monkeypatch):
    monkeypatch.setattr(core.config, "settings", settings_external)
    output = utils.process.check_output(("echo", "-n", echo_str))
    assert output == echo_str


def test_check_output_executable_argument(monkeypatch):
    monkeypatch.setattr(core.config, "settings", settings_external)
    output = utils.process.check_output(("dummy", echo_str), executable=executable)
    assert output == arg1echo(echo_str)


def test_check_output_single_string_arguments(monkeypatch):
    monkeypatch.setattr(core.config, "settings", settings_external)
    output = utils.process.check_output(executable)
    assert output == arg1echo("")


def test_check_output_missing_redirected_executable(monkeypatch):
    monkeypatch.setattr(core.config, "settings", settings_external)
    with pytest.raises(OSError) as error:
        utils.process.check_output(("cat",))
    assert error.value.errno == errno.ENOENT


def test_check_output_ignore_on_shell(monkeypatch):
    monkeypatch.setattr(core.config, "settings", settings_external)
    output = utils.process.check_output("echo -n {}".format(echo_str), shell=True)
    assert output == echo_str
