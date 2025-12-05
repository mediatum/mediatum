# Change Log
All notable changes to mediaTUM will be documented in this file.

## [v2025.12] - 2025-12-05

### Changed
- XML node import properly complains about invalid XML
### Fixed
- hgroup, vgroup display
- correct default smtp server ports (depending on `smtp-server.encryption`)
- XML export includes multiple assigned Mappings to a Mask
- pending workflow documents are no longer exported with XML Workflow exports

## [v2025.10] - 2020-10-10

- mediatum is now licensed under AGPL 3.0+ (see the file COPYING).

- New Features
  - New Workflowsteps:
    - Classify by Attribute
      Institute is stored in the workflowstep attribute "target-attribute-name" as key.
      Processing node will be appended to nodes where their identifies are found in
      processing node attributes key.

    - Defer Processing
      This workflow step simply keep processing node in this state.

    - Forking workflow
      Simply forwards nodes without altering them.  The administrator must declare the name of a metadata attribute.  If a node that is processed by this step type has a non-empty content in that metadata attribute, it will be forwarded to the "true" step, otherwise to the "false" step.

    - hierarchical choice
      This workflow step enables user to assign an institute to a document as node in Database
      The hierarchical structure of institutes is stored in file attached to this workflow step
      and it is presented to user in form of a selection tree. Fieldname for institute is stored
      in workflowstep attribute "target-attribute-name" as key and selected institute is stored in
      node attribute key.

    - Join Metafields
      Implements the workflow step class `JoinMetafields`.
      This class simply takes the contents of several
      (admin-defined) metafields and concatenates them,
      optionally with a separater string in between.

    - Generate Metadata from Metafield
      This workflow step enables user to assign metadata from metafield to node. Metafield is stored in
      workflowstep attribute "source-attribute-name" as key and specifies institute. Institutes contain (key-value) pairs
      as metadata are stored in file attached to this workflow step in form of tree structure.
      If processing node attribute key is found in file then its attributes
      will be set or removed to these (key-value) pairs (removed in case of value is None).

    - DOI register
      This workflow step enables user to contact DataCite that provides persistent identifiers (DOIs specifically)
      for research data and other research outputs.
      The basic operations of the DataCite REST API:
          * Retrieving a single DOI
          * Retrieving a list of DOIs
          * Creating DOIs with the REST API
          ...

    - Set Metadatatype and Schema
      This workflow step enables user to assign node.type and node.schema.
      Type is stored in node attribute specified by the workflowstep attribute "type-attribute"
      and schema in node attribute specified by the workflowstep attribute "schema-attribute".

    - set node name
      the step sets the node name from a selectable attribute

    - Generate Metadata from Template
      This workflow step enables user to assign template from metafield to node. Metafield is stored in
      workflowstep attribute "target-metadata-name".
      If processing node attribute specified by the workflowstep attribute "target-metadata-name".

    - Update Attributes fixed
      (key-value) pairs as metadata are stored in file attached to this workflowstep.
      Processing node attrs will be set or removed according to these (key-value) pairs,
      removed in case value is None.

  - emails may now be sent via encrypted and authenticated SMTP connection
  - 'upload node' workflowstep can restrict permitted mimetypes
  - acme.sh is now included in the nix-shell environment for easy acquisition of Let's Encrypt certificates.
  - Database may now be accessed via a UNIX socket
  - SIGHUP instead of SIGUSR1 is used to reopen logfile (e.g. via logrotate)

- Static files for the webserver root are no longer included in the source repository and need to be downloaded
  during installation/update.
  To do so, issue the command `nix build ${mediatum-source-repo-dir}/static.nix -o ${some-new-dir-for-the-symlink}/static`.
  Then include `${some-new-dir-for-the-symlink}` in the (pipe-separated) list `paths.webroots` in the backend configuration file `mediatum.conf`.

- Backward incompatiblities
  - removed functionalities
    - archive manager
    - print
    - z3590
    - node_alias table in database
    - zoomtiles
    - removed workflowsteps
      - AddPictureToPDF
      - add to folder
      - Check Content
      - File-Attachment
      - Condition
    - remove metadatatypes
      - dynamic valuelist
      - hierarchical list
      - memo
      - message
      - multilist
      - node selection field
      - combination field
      - MDT-m_upload field
      - watermark
  - Workflows must have unique name (ensure this before updating)
  - editor masks must not have two metafields with similar names
  - metadatatypes must not have two metafields with similar names
    similar means: names must be non-empty and unique withon one mask, metadatatype, even when
    only only alphanumerics and underscores are considers (ensure this before updating)
  - workflow names must be unique (ensure this before updating)
  - unsent email is not allowed to edit
  - nginx X-Accel is now configured per directory in mediatum.conf
  - all collection node with exactly one image is used as logo
  - esc(esc(..)) and desc(..) and cdata(..)) and config_get(..) must be removed from tal templates.
    Use 'host_url_join' in place of 'config_get("host.name")', and ` for proper escaping.
  - all startpages must fulfill xml-specification
  - versioning of nodes is now exclusively handled by a dedicated editor module and menu entry
  - searching nodes now skips orphaned nodes, i.e., only searches in the root collection
  - mediatum startscript: 'bin/mediatumrun.py' instead of 'mediatum.py'

- Now uwsgi is used. This needs a new configuration file: uwsgi.yaml and a new command line:
  'uwsgi --yaml uwsgi.yaml'
  example for a minimal uwsgi.yaml:
  ```
  uwsgi:
    plugin: python2
    chdir: /home/%U/git/mediatum
    mount: /app1=bin/mediatumrun.py
    callable: flask_app
    socket: /run/user/%u/mediatum-uwsgi.sock
    locks: 16
    logto: %d/mediatum.log
    cache2: name=mediatumcache,items=4
    pidfile: %d/uwsgi.pid
    logger: file:%d/mediatum.log
  ```

- Changes in config files:
  - nginx.conf: mediatum now only uses the Cookie "mediatum_session".

- metadata/list: handle list structures as JSON/YAML: "'list' metafield predefined values must now be declared as JSON/YAML structure"

- During the update from v2020.04 to v2025.09, several intermediate revisions need to be checked out and used to update database content:
  During "alembic upgrade head" some legacy types are removed from the database.
  To avoid running "alembic upgrade head" into an error, please set following in `mediatum.conf`:
  ```
  [config]
  stub_undefined_nodetypes = true
  fail_if_undefined_nodetypes = false
  ```

  The following commits of the git history contain major updates of the PostgreSQL database version.
  You must export the datebase before reaching such a commit (with the old PostgreSQL version's `pg_dump`), then import the datebase into a fresh cluster (with `initdb` and `pg_restore`) after passing the commit:

  - commit 344c3844d: PostgreSQL version 14.1
  - commit 97edfe90f: PostgreSQL version 15.3
  - commit c6b058600: PostgreSQL version 17.5

## [v2020.04] - 2020-04-17

- This version requires changes to the database scheme:
  before running an existing installation with this version,
  the command "`alembic upgrade head`" must be invoked

### Added

### Changed

- `fts` table is dropped, search is made in the attrs und fulltext column of the node table;
  missing search indices are created at mediatum startup,
  this make need a considerable amount of time
- use ghostscript 9.25 for security reasons
- editor: expand datefields to standard format in doi/bibtex import
- improve server performance when handling
  sorfields or metafield value lists
- admin: sort workflowstep nodes alphabetically
- enhancements for logging and threadstatus

### Fixed

- editor: fix (display of) error message if
    - publishing fails
    - processing an uploaded file fails
    - a bibtex/doi import with broken date is to be published
- editor: enable upload of images with suffix .tif again
- editor: fix error that could lead to invalid html
- admin: fix css to show menu
- admin: workflow export no longer exports its data nodes
- workflow: Step `TextPage` no longer skips its next stop


## [v2019.100] - 2019-10-10

### Added

- workflowstop `addtofolder`

### Changed

- new editor layout with a new menu structure, which needs an "alembic upgrade head"
- refactor code to prepare for migration from athana to flask; this changes some module paths (might require adaption of plugins)

### Fixed

- maximum size of uploaded images is configurable
- bibtex import: correct error handling for incorrect date format
- pdf text extraction with NULL bytes
- editor: folders at uppermost level can be moved


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

