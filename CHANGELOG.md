# Change Log
All notable changes to mediaTUM will be documented in this file.

We mostly follow the conventions given in [Keep a Changelog](http://keepachangelog.com/) and relase a new version roughly once a month.
Calendar Versioning is used for our version numbers: http://calver.org/

## [v2016.11] - 2016-12-16

### Changed

- Converted more TAL templates to Pug (ex-Jade) format
- Frame templates can now be customized in plugins by inheriting from builtin template pieces instead of replacing everything
- print view: deliver PDF with correct file ending

### Fixed

- BibTeX import
- Various frontend fixes, see git log
- Various editor fixes
- Various admin fixes
- mediatum.py --force-test-db 


## [v2016.10] - 2016-11-04

This is a large release with many incompatible changes. Only PostgreSQL is supported as main database and full text search DB from now on
Please contact us at mediatum@ub.tum.de before trying to migrate to this version!

### Changed

- Switched to PostgreSQL
- MySQL and SQLite are no longer supported
- Many more changes (will be documented later)

