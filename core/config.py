#!/usr/bin/python
"""
XXX: This module should be replaced by stdlib's `inifile` or something better.

Use config.get() for string values. There are specialized functions for int, float and bool like in `inifile`:

* config.getint()
* config.getboolean()
* config.getfloat()

Additionally, we have the convention to represent lists as comma-separated values:

    key=value1,value2,value3


Whitespace around commas is stripped from values.

A list can be fetched with `config.getlist()`.
"""
from __future__ import print_function
import logging
import os
import sys
import codecs
import tempfile

logg = logging.getLogger(__name__)

basedir = os.path.abspath(__file__).rsplit(os.sep, 2)[0]
# append our own fallback lib directory
sys.path.append(os.path.join(basedir, "external"))

#: set to True in initialize() if no config file was found
is_default_config = None
#: holds the loaded / default config values
settings = None
#: parsed form of the config key 'i18n.languages' (list)
languages = None


class ConfigException(Exception):
    pass


def get_default_data_dir():
    home = os.path.expanduser("~")
    default_data_dir = os.path.join(home, "mediatum_data")
    return default_data_dir


def get_config_filepath(config_filename=None):
    """Looks for a config file and returns its path if found, in the following order:
    1. MEDIATUM_CONFIG env var
    3. <mediatum_install_dir>/<config_filename> (for example, the git working dir in development)
    2. ~/.config/mediatum/<config_filename>
    4. None (use default config)
    """
    
    if config_filename is None:
        config_filename = "mediatum.cfg"

    env_config_filepath = os.getenv("MEDIATUM_CONFIG")
    if env_config_filepath:
        return env_config_filepath

    basedir_config_filepath = os.path.join(basedir, config_filename)
    if os.path.exists(basedir_config_filepath):
        return basedir_config_filepath

    home_config_filepath = os.path.join(os.path.expanduser("~/.config/mediatum"), config_filename)
    if os.path.exists(home_config_filepath):
        return home_config_filepath

    
def get_guest_name():
    return settings.get("user.guestuser", "guest")


def get(key, default=None):
    return settings.get(key, default)


def getboolean(key, default=None):
    val = get(key)
    if not val:
        return default

    val = val.lower()

    if val in ("true", "yes", "1", "on"):
        return True
    elif val in ("false", "no", "0", "off"):
        return False
    else:
        raise ConfigException(key + ": boolean config value must be true|false, yes|no, 1|0 or on|off")


def getlist(key, default=None):
    val = get(key)
    if not val:
        return default

    spl = val.split(",")
    return [e.strip() for e in spl]


def getint(key, default=None):
    val = get(key)
    if not val:
        return default

    try:
        return int(val)
    except:
        ConfigException(key + ": config value cannot be parsed as integer value")


def getfloat(key, default=None):
    val = get(key)
    if not val:
        return default

    try:
        return float(val)
    except:
        ConfigException(key + ": config value cannot be parsed as float value")


def getsubset(prefix):
    options = {}
    for k, v in settings.items():
        if k.startswith(prefix):
            k = k[len(prefix):]
            if k[0] == '.':
                k = k[1:]
            options[k] = v
    return options


def resolve_datadir_path(path):
    """Resolves paths relative to the datadir location"""
    return os.path.join(get("paths.datadir"), path)


def get_default_zoom_dir():
    return resolve_datadir_path(u"zoom_tiles")


def _read_ini_file(basedir, filepath):
    lineno = 0
    params = {}

    with codecs.open(filepath, "rb", encoding='utf8') as fi:
        module = ""
        for line in fi.readlines():
            lineno = lineno + 1
            # remove comments
            hashpos = line.find("#")
            if hashpos >= 0:
                line = line[0:hashpos]
            # remove whitespace
            line = line.strip()

            if line == "":
                pass  # skip empty line
            elif line[0] == '[':
                if line[-1] != ']':
                    raise ValueError("Syntax error in line {} of file {}:\n{}".format(lineno, filepath, line))
                module = line[1:-1]
            else:
                equals = line.find("=")
                if equals < 0:
                    raise ValueError("Syntax error in line {} of file {}:\n{}".format(lineno, filepath, line))
                key = module + "." + line[0:equals].strip()
                value = line[equals + 1:].strip()
                if(len(value) and value[0] == '\'' and value[-1] == '\''):
                    value = value[1:-1]
                params[key] = value

    # add the filepath from where the config was loaded.
    # This could differ from get_config_filepath() called at a later time, but that's quite unrealistic ;)
    params["config.filepath"] = filepath
    return params


def check_create_dir(dirpath, label):
    """Checks if dir with `dirpath` already exists and creates it if it doesn't exists.
    :param dirpath: path of directory
    :param label: short, readable directory description to show in messages
    """
    dirpath = os.path.expanduser(dirpath)

    if not os.path.isabs(dirpath):
        print("CONFIG ERROR 1, path must be absolute: {} ({})".format(dirpath, label))
        sys.exit(1)

    if not os.path.exists(dirpath):
        try:
            os.mkdir(dirpath)
        except OSError as e:
            print("CONFIG ERROR 2, couldn't create directory '{}' ({}): {}".format(dirpath, label, e.strerror))
            sys.exit(2)

        print("created directory '{}' ({})".format(dirpath, label))

    elif not os.path.isdir(dirpath):
        print("CONFIG ERROR 3, path is not a directory: '{}' ({})".format(dirpath, label))
        sys.exit(3)
    else:
        print("found dir '{}' ({})".format(label, dirpath))


def set_default_values():
    if not "paths.datadir" in settings:
        settings["paths.datadir"] = get_default_data_dir()

    if not "paths.tempdir" in settings:
        settings["paths.tempdir"] = tempfile.gettempdir()

    if not "paths.zoomdir" in settings:
        settings["paths.zoomdir"] = get_default_zoom_dir()


def expand_paths():
    for confkey in ["paths.datadir", "paths.tempdir", "paths.zoomdir", "logging.file"]:
        if confkey in settings:
            settings[confkey] = os.path.expanduser(settings[confkey])


def fix_dirpaths():
    for confkey in ["paths.datadir", "paths.tempdir"]:
        if confkey in settings:
            # we need the trailing slash because concatenation is used in some places in the codebase.
            # XXX: remove this when all concatenations are replaced by os.path.join()!
            if not settings[confkey].endswith("/"):
                settings[confkey] += "/"


def initialize(config_filepath=None, prefer_config_filename=None):
    '''
    :param config_filepath: absolute path to the config file. Overrides default config file locations.
    :param prefer_config_filename: name of an alternative config file. Uses mediatum.cfg if nothing is given or file doesn't exist. 
        This file name is searched in the mediatum basedir and ~/.config/mediatum, in that order.
    '''
    
    if config_filepath and prefer_config_filename:
        raise Exception("specify config_filepath or prefer_config_filename, but not both!")
    
    if not config_filepath and prefer_config_filename:
        # no path given, try preferred config file name first
        config_filepath = get_config_filepath(prefer_config_filename)
        
    if not config_filepath:
        # (still) no path, try (again) with default config name
        config_filepath = get_config_filepath()
        

    global settings, languages, is_default_config

    if config_filepath is not None:
        print("using config file at", config_filepath)
        settings = _read_ini_file(basedir, config_filepath)
        is_default_config = False
    else:
        print("WARNING: config file", config_filepath, "not found, using default test config!")
        settings = {}
        is_default_config = True

    set_default_values()
    expand_paths()
    fix_dirpaths()

    languages = [lang.strip() for lang in settings.get("i18n.languages", "en").split(",") if lang.strip()]

    # create dirs if neccessary
    data_path = settings.get("paths.datadir")

    check_create_dir(data_path, "datadir")
    check_create_dir(os.path.join(data_path, "html"), "datadir/html")
    check_create_dir(settings.get("paths.tempdir"), "tempdir")
    check_create_dir(os.path.join(data_path, "incoming"), "incoming")
    check_create_dir(settings.get("paths.zoomdir"), "zoomdir")

    # extract log dir from log file path and create it if neccessary
    log_filepath = settings.get("logging.file")
    if log_filepath:
        log_dirpath = os.path.dirname(log_filepath)
        check_create_dir(log_dirpath, "dir for logging.file")
        
    # create log dir if specified
    log_dirpath = settings.get("logging.dir")
    if log_dirpath:
        check_create_dir(log_dirpath, "log dir")



def check_create_test_db_dir():
    data_path = settings.get("paths.datadir", get_default_data_dir())
    dirpath = os.path.join(data_path, "test_db")
    check_create_dir(dirpath, "datadir/test_db")
    return dirpath

#
# resolve given filename to correct path/file
#


def resolve_filename(filename):
    templatepath = settings.get("template.path", "")
    templatename = settings.get("template.name", None)
    if templatepath.startswith("/") or templatepath.startswith("\\"):
        pathlist = [templatepath]
    else:
        pathlist = [basedir, templatepath]
    if templatename:
        pathlist += [templatename]
    pathlist += [filename]

    newname = os.path.join(*pathlist)
    if os.path.exists(newname):
        return newname
    else:
        if filename.find("admin_") >= 0:
            return pathlist[0] + "/admin/template/" + filename
        elif filename.startswith("m_"):
            return pathlist[0] + "/metatypes/" + filename
    return filename
