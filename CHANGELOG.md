# Change Log
All notable changes to mediaTUM will be documented in this file.

We mostly follow the conventions given in [Keep a Changelog](http://keepachangelog.com/) and relase a new version roughly once a month.
Calendar Versioning is used for our version numbers: http://calver.org/


## [v2019.021] - 2019-04-02

### Fixed

- fix missing csrf in default login template


## [v2019.02] - 2019-02-28

### Added

- cross side request forgery
- metadatascheme translated
- choosing directories translated
- filename of attachments is preserved
- pkgs.glibcLocales
- enable change of document nodename
- CC0 license
- pidfile can be configured

### Changed

- postgresql 10.3
- all packages from nixos 18.03
- table fts with new primary key
- disable delete user
- expand z3950 logging
- use convert from graphicsmagick instead of imagemagick

### Fixed

- export.js
- print failes if metadata not unicode
- from field from searchfield is not resetted


## [v2018.09] - 2018-09-26

### Added

- memory statistics page
- session expiration time

### Changed

- bibtex import set creationtime
- Acceleration of print function
- improve frontend responsiveness

### Fixed

- statistics: flush temporary file
- serving transfer zip archives may fail
- login template language aware
- memory leak sql statements not freed
- security gap in uri
- http response header: consider utf8 characters in Content-Disposition


## [v2018.04] - 2018-04-18

### Added

- new config parameter ldap.auto_create_user
- systemd templates

### Changed

- nix-shell with nginx 1.12.1
- new jquery version 1.12.4
- export.js with relative path to to jquery_min.js
- bibtex- / doi-import: set all metadata

### Fixed

- close tempfiles correctly
- deny access to system files
- f/admin user: relative link for user_home_dir
- cross site scripting
- inhibit http response splitting by crlf injection
- metafields of type list: fix multiple selections 
- chkeditor problems with special utf8 characters


## [v2018.01] - 2018-01-29

### Added

- preparation for logrotation (but not activated)
- unaccent_german_umlauts_special.rules for postgres search added to nix-shell

### Changed

### Fixed

- simultaneously editing test and memo fields not possible
- quickpublisher errormessages hided behind other objects
- creating workflowsteps with the same name
- node with childnodes use same link for thumbnail and details
- alembic cleanup


## [v2017.09] - 2017-10-17

### Added

- initial data with access rules for administrator and guest 
- metis tracking pixel

### Changed

### Fixed

- search in editor leads to exception
- restore from archive blocks all threads


## [v2017.06] - 2017-08-10

### Added

- include meta tags for google scholar

### Changed

- acceleration of search
- add new container at top navigation tree
- attachmentbrowser support also mp4
- links in htmlmemo field enabled
- access of localhost are not used for statistics data
- globally most occurring schema is used instead of limiting to container content

### Fixed

- metadata field cannot be changed
- search in edit area leads to exception by special characters
- wrong email address blocks workflow
- prevent adding node as child to itself
- access to older version of a image returns an error
- older version of digital objects are not shown if only metadata has changed
- python type mismatches in handling of metafields of type union


## [v2017.05] - 2017-06-27

### Added

- workflow diss: log date of publishing

### Changed

### Fixed


## [v2017.03] - 2017-04-04

### Added

### Changed

### Fixed

- access to lower versions of a document returns an error
- wrong errormessage during upload of a file with a new version
- meta informations cannot be extracted from a pdf-document
- pdf metadata extraction problem
- too restrictive editor which denied upload of new files for some types


## [v2017.02] - 2017-03-16

### Added

- edit area with pagination to accelerate editor

### Changed

- upgraded to Nix packages 16.09
- removed obsolete edit modules: frontendparts, lza, ftp, license
- removed obsolete function for creating hashes in the identifier edit module
- removed obsolete ftp upload function
- removed obsolete upload webservice
- removed obsolete javascript zoom for image content type
- removed obsolete content types ImageStream and Project
- removed obsolete workflow steps ldapauth and checkdoublet
- removed obsolete meta field password
- removed obsolete metadata web service
- accelerate display of user statistics
- javascript zoom for images removed

### Fixed

- edit: moving files to subfolders in the edit area
- editmask with watermark metadata field cannot be saved
- editor linking child object detail to frontend
- various bugfixes


## [v2017.01] - 2017-02-14

### Changed

- removed obsolete integrated help
- check type of uploaded file when trying to exchange the digital object
- removed preview editor function for containers
- performance improvements

### Fixed

- problems when running mediaTUM without a config file
- Bibtex-Upload: accept non-standard records like @SCIENCEREPORT
- missing occurences list for search queries
- missing license icons
- Bibtex: www-address
- various bugfixes


## [v2016.12] - 2016-01-24

### Added

- Frontend: Users can change the number of displayed nodes in list views
- Example content for empty database: example schemas
- Citation type proceedings-article now allowed in DOI import

### Changed

- Better styling for headings: they don't look like links anymore
- Editor: start with user uploads dir instead of collections root

### Fixed

- Upload of files with umlauts or other non alphanumeric characters in the file name
- Display of version HTML
- Metafield name doublet creation
- Errors in mediatum configuration template
- More robust handling of bibtex file names


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

