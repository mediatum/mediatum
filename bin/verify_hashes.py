#! /usr/bin/env nix-shell
#! nix-shell -i python -p python

import sys
sys.path.append(".")  # run from mediatum root: bin/verify_hashes.py

import os
import time
import logging
import configargparse
from pprint import pprint

# third-party imports
from sqlalchemy import or_

# local imports
from core.init import basic_init
basic_init()

from core import db
from core.database.postgres.file import File
from core.database.postgres.node import Node


logg = logging.getLogger(__file__)
identifier_importers = {}
q = db.query
s = db.session

HASH_FILETYPES = File.ORIGINAL_FILETYPES


def verify_hash(_file):
    print('\n--')
    logg.info('File: %s', _file)
    pprint(_file.to_dict())
    hash_ok = _file.verify_checksum()
    s.commit()

    file_found = os.path.isfile(_file.abspath)
    logg.info('file found: %s', file_found)
    if file_found:
        logg.info('File: %s', _file.abspath)
        logg.info('  - size: %s', _file.size_humanized)
        logg.info('  - ismount: %s', os.path.ismount(_file.abspath))
    return hash_ok


def verify_hashes(files, **kwargs):
    MEGA = 1024. ** 2
    cnt = 0
    total_size = 0
    total_hours = 0
    start_time = time.time()
    if files is None:
        files = []
    print('')
    for _file in files:
        file_size = _file.size
        if kwargs['ignore']:
            extension = os.path.splitext(_file.path)[1]
            if extension and extension.lower() in kwargs['ignore']:
                logg.info('Ignoring file %s', _file.path)
                continue
        if kwargs['smaller_MB'] and file_size > kwargs['smaller_MB'] * MEGA:
            logg.debug('too large')
            continue
        if kwargs['larger_MB'] and file_size < kwargs['larger_MB'] * MEGA:
            logg.debug('too small')
            continue
        if file_size:
            if kwargs['total_size_MB'] and (total_size + file_size >= kwargs['total_size_MB'] * MEGA):
                logg.info('Total size limit reached.')
                break
            total_size += file_size
        hash_ok = verify_hash(_file)
        if hash_ok:
            sys.stdout.write('-OK-')
        else:
            sys.stdout.write('-F-')
        cnt += 1
        total_hours = (time.time() - start_time) / 3600.
        if kwargs['max_hours'] and kwargs['max_hours'] < total_hours:
            logg.info('Verification of checksums interrupted after %f hours as requested.', total_hours)
            break
        if kwargs['limit'] and cnt == kwargs['limit']:
            logg.info('Verification of checksums interrupted after %i files as requested.', kwargs['limit'])
            break
    print('')
    logg.info('Verified checksums of %i files, %i bytes processed in %.2f hours', cnt, total_size, total_hours)
    s.commit()
    print('')


def stats():
    """ Return some statistics about checksum coverage. """
    all_files = q(File).filter(File.filetype.in_(HASH_FILETYPES))
    count_files = all_files.count()
    count_ok = all_files.filter(File.sha512_ok).count()
    pct_ok = count_ok / float(count_files) * 100.
    count_not_ok = all_files.filter(File.sha512_ok == False).count()
    pct_not_ok = count_not_ok / float(count_files) * 100.
    count_unknown = all_files.filter(File.sha512_ok == None).count()
    pct_unknown = count_unknown / float(count_files) * 100.

    logg.info("%8i of %8i original files (%7.4f %%) are verified by checksum.",
              count_ok, count_files, pct_ok)
    logg.info("%8i of %8i original files (%7.4f %%) have unknown checksum state.",
              count_unknown, count_files, pct_unknown)
    logg.info("%8i of %8i original files (%7.4f %%) do have a checksum that does not match with the stored value.",
              count_not_ok, count_files, pct_not_ok)
    return {'count_all_files': count_files,
            'count_hash_ok': count_ok,
            'pct_ok': pct_ok}


def main():
    parser = configargparse.ArgumentParser("mediaTUM " + __file__)
    parser.add_argument("-N", "--limit", type=int, default=None,
                        help="Max. number of files to process.")
    parser.add_argument("--path", type=str, default=None, help="Path or substring of path.")
    parser.add_argument("--total-size-MB", type=float, default=None,
                        help="The maximum total amount of data processed in this run.")
    parser.add_argument("--max-hours", type=float, default=None,
                        help="Maximum total duration of this run in hours.")
    parser.add_argument("--ignore", type=str, action='append', default=None,
                        help="File extensions to be ignored.")
    parser.add_argument("--offset", type=int, default=None,
                        help="Offset value.")

    # filter-options for file size
    size_limit = parser.add_mutually_exclusive_group()
    size_limit.add_argument("--smaller-MB", type=float, help="Max. file size in megabytes.")
    size_limit.add_argument("--larger-MB", type=float, help="Min. file size in megabytes.")
    # sort-options for checksum age
    sort_time = parser.add_mutually_exclusive_group()
    sort_time.add_argument("--newest-first", action="store_true",
                           help="Verify newest checksums first.")
    sort_time.add_argument("--oldest-first", action="store_true",
                           help="Verify oldest checksums first.")
    # filter-options for checksum status
    ok_group = parser.add_mutually_exclusive_group()
    ok_group.add_argument("--ok", action="store_true",
                          help="Only verify files with successful last check.")
    ok_group.add_argument("--not-ok", action="store_true",
                          help="Only verify files with missing or bad last check.")
    ok_group.add_argument("--unknown", action="store_true",
                          help="Only verify files with missing last check.")

    parser.add_argument("--node-id", type=int, default=None,
                        help="Verify checksums for files of node with given ID.")
    parser.add_argument("--file-id", type=int, default=None,
                        help="Verify checksum for file with given ID.")

    parser.add_argument("-i", "--info", action="store_true",
                        help="Print checksum statistics and return")

    print('\n** %s **' % __file__)

    args = parser.parse_args()

    if args.ignore:
        ignored_ext = []
        for ext in args.ignore:
            if not ext.startswith('.'):
                ext  = '.' + ext
            ignored_ext.append(ext.lower())
        args.ignore = ignored_ext

    pprint(args)

    if args.info:
        stats()
        return

    files = q(File).filter(File.filetype.in_(HASH_FILETYPES)).order_by(File.id)
    # test queries:
    #   files = files.filter(File.path.like(u'%820042226488%'))
    #   files = q(File).filter(File.mimetype == 'image/jpeg').limit(10)

    # filter and sort the files to verify based on command line options
    if args.path:
        files = files.filter(File.path.like(u'%{}%'.format(args.path)))
    if args.newest_first:
        files = files.order_by(None)  # reset order_by
        files = files.order_by(File.sha512_checked_at.desc())
    if args.oldest_first:
        files = files.order_by(None)  # reset order_by
        files = files.order_by(File.sha512_checked_at)
    if args.ok:
        files = files.filter(File.sha512_ok)
    if args.not_ok:
        files = files.filter(or_(File.sha512_ok == False, File.sha512_ok == None))
    if args.unknown:
        files = files.filter(File.sha512_ok == None)
    if args.node_id:
        node = q(Node).get(args.node_id)
        if node:
            files = node.files.filter(File.filetype.in_(HASH_FILETYPES))
        else:
            files = []
    if args.file_id:
        files = files.filter(File.id == args.file_id)
    if args.limit:
        files = files.limit(args.limit)
    if args.offset:
        files = files.offset(args.offset)

    verify_hashes(files, **vars(args))
    stats()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("%s stopped by KeyboardInterrupt." % __file__)
        sys.exit(1)
