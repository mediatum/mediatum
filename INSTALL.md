# mediaTUM - Installation

## Getting mediaTUM

* Clone the repository: `git clone https://mediatumdev.ub.tum.de/mediatum.git -b postgres`

## Nix Installation

This should work on all Linux distributions and Mac OS X (Mac untested, but give it a try and report problems!).
You need the [Nix package manager](https://nixos.org/nix) (version > 1.8) to use this.
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

You should use Nix instead. We don't support this installation method at the moment.
If you really want to install everything by yourself, here are some hints:

* install `python 2.7`, `postgresql 9.5` (postgres database server), `libpq-dev` (postgres client library)
* Optional:
  * external program for video support: `ffmpeg`
  * for image support: `exiftool`, `imagemagick`
  * for workflow graphics: `graphviz`
* Python dependencies can be found in `requirements.txt`, we recommend using a
[virtual python environment](http://docs.python-guide.org/en/latest/dev/virtualenvs/) (virtualenv) for dependency
management:
  * create a virtualenv for mediaTUM in the `venv` directory: `virtualenv -p python2.7 venv`
  * activate virtualenv with `source venv/bin/activate`
  * within the virtualenv, install python deps with `pip install -r requirements.txt`
  * HINT: Do not commit the venv directory to your git repository!


## MediaTUM Config File

See `mediatum.cfg.template` for default values. Copy this file to `mediatum.cfg` and edit.

Most important sections:

-   \[database\]: database connection
-   \[paths\]: where to store data
-   \[host\]: set host name and port


## Database Setup

MediaTUM stores its information in a Postgres database within the schema `mediatum`.
A database user / role should be created for mediaTUM.
The database must have the `hstore` extension.

Example database setup (using `psql`):

    CREATE USER mediatum;
    \password mediatum
    CREATE DATABASE mediatum OWNER mediatum;
    \c mediatum
    CREATE EXTENSION hstore SCHEMA public;

By default, mediaTUM uses the `public` schema to look for extensions.
If you have created `hstore` in another schema, for example `extensions`, set this in `mediatum.cfg`:

    [database]
    extension_schema=extensions


## Database Schema Setup

The schema will be created by the following command:

    bin/manage.py schema create


## Loading Default Data

Default data for an empty mediaTUM instance can be loaded by:

    bin/manage.py data init


## Start mediaTUM

MediaTUM can be started like that if you want to use the python interpreter in your PATH (possibly in a virtualenv or nix shell):

    python start.py
