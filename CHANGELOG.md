# Change Log
All notable changes to mediatum will be documented in this file.

## [Unreleased] - 2016-10-04

### Changed
- New versioning based on sqlalchemy-continuum
- Schema change to split between node and file, file table and file-node link-table introduced.
- New access control system, based on PostgreSQL queries: #52daccf4800db3

  

This change log mostly follows the conventions given in http://keepachangelog.com/