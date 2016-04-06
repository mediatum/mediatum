# mediaTUM - Python Document Server

mediaTUM is an open source software product for large scale image, document and video archiving and retrieval written in Python.
For more information and contributions [contact us](mailto:mediatum@ub.tum.de).

## DEV WARNING

Warning: This is a development version!

## Developers

-   mediaTUM development team @ Technische Universität München
-   external contributors

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

See `INSTALL.md` for more details on installation and usage.
