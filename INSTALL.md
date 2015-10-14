# mediaTUM - Installation

TODO


## Nix Installation

(for Linux and MacOS)

## Manual Installation

(for Windows, TODO)

* install python 2.7, postgresql 9.4
* optional: ffmpeg, exiftool, graphviz
* Python dependencies can be found in `requirements.txt`
* Create virtualenv for mediaTUM
* Install python deps with `pip install -r requirements.txt` (use virtualenv!)

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

To use automatic dependency setup with Nix, use:

    ./start.py

MediaTUM can be started with like that if you want to use the python interpreter in your PATH (possibly in a virtualenv):

    python start.py
