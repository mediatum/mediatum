# mediaTUM - Installation

## Getting mediaTUM

* Clone the repository: `git clone https://mediatumdev.ub.tum.de/mediatum.git -b postgres`

## Nix Installation

(for Linux and MacOS)

This should work on all Linux distributions and MacOS. You need the [Nix package manager](https://nixos.org/nix) (version > 1.8) to use this.
On non-NixOS machines, about 1,5GB disk space is required. On NixOS, about 1GB is required.


### Nix Shell (Developer)

Go to the `mediatum` directory and run:

    nix-shell

All binaries including the python interpreter with all needed dependencies are available from this shell.
Updates are done automatically every time `nix-shell` is run.

The python interpreter link can be built with

    nix-build python.nix -o pythonenv

The interpreter at `pythonenv/bin/python` can be used to run mediaTUM, like in a virtualenv.
This interpreter path should be used for IDEs like PyCharm or PyDev.

### Nix Package Installation (Server)

TODO


## Manual Installation

(for Windows, TODO)

* install python 2.7, postgresql 9.4
* optional: ffmpeg, exiftool, graphviz
* Python dependencies can be found in `requirements.txt`
* create virtualenv for mediaTUM
* install python deps with `pip install -r requirements.txt` (use virtualenv!)

## Database Setup

MediaTUM stores its information in a Postgres database within the schema _mediatum_.
A database user / role should be created for mediaTUM.
The database must have the `hstore` extension, usable without schema qualification.
One way to accomplish this is to set the search path to _mediatum,public_ and create the extension in schema public.


Example database setup (using `psql`):

    CREATE USER mediatum;
    \password mediatum
    CREATE DATABASE mediatum OWNER mediatum;
    ALTER DATABASE mediatum SET search_path TO mediatum,public;
    \c mediatum
    CREATE EXTENSION hstore SCHEMA public;

### MediaTUM Config File

See `mediatum.cfg.template` for default values. Copy this file to `mediatum.cfg` and edit.

Most important sections:

* [database]: database connection
* [paths]: where to store data
* [host]: set host name and port


## Database Schema Setup

The schema will be created by the following command:

    bin/manage.py schema create


## Loading Default Data

Default data for an empty mediaTUM instance can be loaded by:

    bin/manage.py data init


## Start mediaTUM

MediaTUM can be started like that if you want to use the python interpreter in your PATH (possibly in a virtualenv or nix shell):

    python start.py
