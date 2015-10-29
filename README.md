# mediaTUM - Python Document Server

mediaTUM is an open source software product for large scale image, document and video archiving and retrieval written in Python.

You can visit public mediaTUM instances

-   Technische Universität München [mediaTUM @ tum.de](http://mediatum.ub.tum.de)
-   Universität Augsburg [mediaTUM @ uni-augsburg.de](https://media.bibliothek.uni-augsburg.de/)

## DEV WARNING

Warning: This is a development version!

## Contact

-  [Contact us](mailto:mediatum@ub.tum.de) for more information

## Features

-   support for document, video and image file formats (pdf, ps, jpeg, png, tif, mp4)
-   user-defined schemas for object metadata (data describing the media object)
-   metadata and fulltext search
-   import document metadata from DOI / Bibtex files
-   user-defined workflows for objects
-   OpenAIRE compliant

### User Management / Access Control

-   user and user group management
-   extensible, rule-based, access control
-   pluggable authentication providers

###   External interfaces

-   REST-compliant Web service
-   OAI export
-   Z39.50 support

### Plugin System

-   write your own plugins: integrate new data types, add authentication providers ...

## Developers

-   mediaTUM development team @ Technische Universität München
-   external contributors

## Contribute

-  You can contribute to the project, [contact us!](mailto:mediatum@ub.tum.de)

## License

All mediaTUM software is licensed under the [GNU General Public License 3](http://www.gnu.org/licenses/gpl.html).
You can redistribute it and/or modify it under the terms of the GPL 3 as published by
the Free Software Foundation.

## Used Tools

* We use [PyVMMonitor](http://pyvmmonitor.com) for profiling, which is free for open source projects


## Quick Test Installation In Three Steps

This should work on all Linux distributions and MacOS. You need the [Nix package manager](https://nixos.org/nix) (version > 1.8) to run this.
On non-NixOS machines, about 1,5GB disk space is required. On NixOS, about 1GB is required.

1. Clone the repository: `git clone https://mediatumdev.ub.tum.de/mediatum.git -b postgres`
2. Go to the mediatum directory: `cd mediatum`
3. Run mediaTUM: `./mediatum.py --force-test-db`

The last line in the output should say _Athana HTTP Server started at http://0.0.0.0:8081_.
You can visit `http://localhost:8081` now. Default login is *admin* with password *insecure*.

The last step downloads all missing dependencies, it may take some minutes on the first run. Dependencies are installed to `/nix/store`.
By default, database, upload and log files are written to `$HOME/mediatum_data`.

