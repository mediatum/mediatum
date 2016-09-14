#!/usr/bin/python
"""
 mediatum - a multimedia content repository

 Copyright (C) 2007 Arne Seifert <seiferta@in.tum.de>
 Copyright (C) 2007 Matthias Kramm <kramm@in.tum.de>

 This program is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.

 This program is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import os
import sys
sys.path += ['../..', '../', '.']

import core.config as config
import logging
import datetime
import time
import urllib2
import re
from lxml import etree
from math import ceil

from core.init import full_init
full_init(prefer_config_filename="sitemap.log")

from core import Node
from core import db
from contenttypes import Collections

q = db.query

# XXX: alias handling must be fixed before switching this on
USE_ALIASES = False
PING_GOOGLE = True
PING_URL_ENCODED = 'http://www.google.com/webmasters/tools/ping?sitemap=http%3A%2F%2Fmediatum.ub.tum.de%2Fsitemap-index.xml'


class Sitemap:

    """
    A sitemap object which holds data relevant to the sitemap and creation of sitemap.xml's
    """

    def __init__(self, path, name, host):
        self.name = name
        self.path = '/'.join([path, 'web', 'root', name])
        self.host = host

    def create_sitemap(self, nodes, p_num):
        """
        Creates a sitemap.xml from the nodes which were passed in
        @param nodes: A list of nodes from the mediatum tree in the format '#*'
        """
        def check_date_format(date):
            """
            Checks to see whether dates are in proper datetime format and converts times in ##/##/#### format to
            datetime or raises an error when it encounters a different format
            """
            # check if date is already in the proper format
            datetime_pattern = re.compile(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$')

            # regex and its accompanying strptime format
            misc_date_formats = ((re.compile(r'\d{2}/\d{2}/\d{4}\+\d{2}:\d{2}T\d{2}:\d{2}:\d{2}$'), '%m/%d/%Y+%H:%MT%H:%M:%S'),
                                 (re.compile(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$'), '%Y-%m-%dT%H:%M:%S'),
                                 (re.compile(r'\d{4}/\d{2}/\d{2}$'), '%d/%m/%YT%H:%M:%S'),
                                 (re.compile(r'\d{4}/\d{2}/\d{2}$'), '%/%d/%YT%H:%M:%S'),
                                 (re.compile(r'\d{2}/\d{2}/\d{4}\+\d{2}:\d{2}$'), '%m/%d/%Y+%H:%M'),
                                 (re.compile(r'\d{4}-\d{2}-\d{2}$'), '%Y-%m-%d'),
                                 (re.compile(r'\d{2}/\d{2}/\d{4}$'), '%d/%m/%Y'),
                                 (re.compile(r'\d{2}/\d{2}/\d{4}$'), '%m/%d/%Y'))

            matched = re.search(datetime_pattern, date)
            if matched:
                return date
            else:
                for date_format_tuple in misc_date_formats:
                    matched = re.search(date_format_tuple[0], date)
                    if matched:
                        try:
                            timestruct = time.strptime(date, date_format_tuple[1])
                            timedatetime = datetime.datetime.fromtimestamp(time.mktime(timestruct))
                            return timedatetime.strftime('%Y-%m-%dT%H:%M:%S')
                        except ValueError:
                            continue
                else:
                    raise TypeError('unknown date format given: %s' % date)

        if os.path.isfile(self.path):
            logging.getLogger('everything').info('Sitemap already exists at %s' % self.path)
        else:
            root = etree.Element('urlset', xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
            # Doesn't create a sitemap if no nodes to place in it
            if not nodes:
                pass
            else:
                for id_lastmod_tuple in nodes:
                    url = etree.SubElement(root, 'url')
                    loc = etree.SubElement(url, 'loc')
                    if 'system.aliascol' in q(Node).get(id_lastmod_tuple[0]).attrs and USE_ALIASES:
                        loc.text = ''.join(['http://', self.host, '/', q(Node).get(id_lastmod_tuple[0]).attrs['system.aliascol']])
                    else:
                        loc.text = ''.join(['http://', self.host, '/node?id=', id_lastmod_tuple[0]])
                    lastmod = etree.SubElement(url, 'lastmod')

                    #remove preexisting time zone indicator
                    stripped_date = id_lastmod_tuple[1].replace('+02:00', '')

                    if stripped_date == '':
                        lastmod.text = ''.join([datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S'), '+02:00'])
                    else:
                        lastmod.text = ''.join([check_date_format(stripped_date), '+02:00'])

                    changefreq = etree.SubElement(url, 'changefreq')
                    changefreq.text = 'monthly'
                    priority = etree.SubElement(url, 'priority')
                    priority.text = p_num
                try:
                    with open(self.path, 'w') as f:
                        f.write('''<?xml version="1.0" encoding="UTF-8"?>\n''')
                        f.write(etree.tostring(root))
                        f.close()
                except IOError:
                    logging.getLogger('error').error('Error creating %s' % self.path)

    def delete_sitemap(self):
        """
        Removes the sitemap from the directory structure /web/root/
        """
        if os.path.isfile(self.path):
            try:
                os.remove(self.path)
            except IOError:
                logging.getLogger('error').error('Error removing %s' % self.path)


class SitemapIndex:

    """
    A sitemap index object. It is responsible for serving as a reference for all sitemaps
    """

    def __init__(self, path, name, host):
        self.name = name
        self.path = '/'.join([path, 'web', 'root', name])
        self.host = host

    def create_sitemap_index(self, sitemaps, cur_time):
        """
        Creates a sitemap index file from the sitemaps passed in
        @param sitemaps: a list of strings of sitemap names
        """
        if os.path.isfile(self.path):
            logging.getLogger('everything').info('%s already exists' % self.path)
        else:
            root = etree.Element('sitemapindex', xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
            if not sitemaps:
                pass
            else:
                for i in sitemaps:
                    sm = etree.SubElement(root, 'sitemap')
                    loc = etree.SubElement(sm, 'loc')
                    loc.text = '/'.join(['http:/', self.host, i])
                    lastmod = etree.SubElement(sm, 'lastmod')
                    lastmod.text = cur_time
                try:
                    with open(self.path, 'w') as f:
                        f.write('''<?xml version="1.0" encoding="UTF-8"?>\n''')
                        f.write(etree.tostring(root))
                        f.close()
                except IOError:
                    logging.getLogger('error').error('Error creating %s' % self.path)

    def delete_sitemap_index(self):
        """
        Removes the sitemapindex from the directory structure /web/root/
        """
        if os.path.isfile(self.path):
            try:
                os.remove(self.path)
            except IOError:
                logging.getLogger('error').error('Error removing %s' % self.path)


def create():
    """
    Creates the sitemap files and the sitemap index files which are located at /web/root/
    """
    logging.getLogger('everything').info('Creating Sitemaps and Sitemap Index...')
    from core.users import get_guest_user

    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    hostname = config.get('host.name')

    root = q(Collections).one()
    guest_user = get_guest_user()
    all_nodes = root.all_children_by_query(q(Node)).filter_read_access(user=guest_user)
    sitemaps = []

    node_dict = {'collection': [],
                 'directory': [],
                 'document': [],
                 'dissertation': [],
                 'image': [],
                 'video': [],
                 'audio': [],
    }

    for node in all_nodes:
        # Arkitekt had a guest field that is actually not visible
        if node.has_read_access(user=guest_user):
            for node_type in node_dict.keys():
                if node_type in q(Node).get(node.id).type:
                    node_dict[node_type].append((unicode(node.id), q(Node).get(node.id).updatetime))

    # Reassign node_dict to a dict where empty values were removed
    node_dict = dict((k, v) for k, v in node_dict.iteritems() if v)

    # Sitemap can have at most 50k entries
    for key in node_dict.keys():
        if key in ('dissertation', 'document', 'image'):
            priority_level = '1.0'
        elif key == 'videos':
            priority_level = '0.8'
        else:
            priority_level = '0.5'

        # Create multiple sitemaps for node lists > 50k
        if len(node_dict[key]) > 50000:
            partitions = int(ceil((len(node_dict[key]) / 50000.)))
            for partition_number in range(partitions):
                sitemap = Sitemap(base_dir, ''.join(['sitemap-', str(key), str(partition_number), '.xml']), hostname)
                sitemaps.append(sitemap.name)
                sitemap.create_sitemap(node_dict[key][partition_number * 50000:(partition_number + 1) * 50000], priority_level)
        else:
            sitemap = Sitemap(base_dir, ''.join(['sitemap-', key, '.xml']), hostname)
            sitemaps.append(sitemap.name)
            sitemap.create_sitemap(node_dict[key], priority_level)

    siteindex = SitemapIndex(base_dir, 'sitemap-index.xml', hostname)
    now = '+'.join([datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S'), '02:00'])
    siteindex.create_sitemap_index(sitemaps, now)

    logging.getLogger('everything').info('Generation of Sitemaps and SitemapIndex Complete')


def clean():
    """
    Removes all .xml files from the /web/root/ directory
    """
    logging.getLogger('everything').info('Cleaning /root of all Sitemaps and SitemapIndex')

    base_dir = os.path.abspath(os.curdir)
    web_root_dir = '/'.join([base_dir, 'web', 'root'])

    sitemaps = [f for f in os.listdir(web_root_dir) if '.xml' in f and f.startswith('sitemap')]

    # If no .xml files exist
    if not sitemaps:
        logging.getLogger('everything').info('Nothing to remove...')
    else:
        for sm in sitemaps:
            logging.getLogger('everything').info('Deleting file: %s' % sm)
            os.remove('/'.join([web_root_dir, sm]))

    logging.getLogger('everything').info('Cleaning Complete...')


def main():
    if len(sys.argv) > 2 or 'create' not in sys.argv and 'clean' not in sys.argv:
        raise TypeError('sitemap.py takes in only one of the following arguments: [create] [clean]')
    elif sys.argv[1] == 'create':
        clean()
        create()
        if PING_GOOGLE:
            response = urllib2.urlopen(PING_URL_ENCODED)
            if response.getcode() == 200:
                logging.getLogger('everything').info(
                    'Successful ping of sitemap-index.xml to Google; Response Code: %i' % response.getcode())
            else:
                logging.getLogger('everything').info(
                    'Unsuccessful ping of sitemap-index.xml to Google; Response Code: %i' % response.getcode())
    elif sys.argv[1] == 'clean':
        clean()

if __name__ == '__main__':
    main()
