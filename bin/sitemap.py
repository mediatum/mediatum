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
__author__ = 'Andrew Darrohn andrew.darrohn@tum.de'

import os
import sys
import codecs
sys.path += ['../..', '../', '.']

from core.init import full_init
full_init()

import core.users as users
import core.acl as acl
import core.tree as tree
import logging
import datetime
import time
import urllib2
import re
from lxml import etree
from ConfigParser import SafeConfigParser
from math import ceil

logg = logging.getLogger(__name__)

USE_ALIASES = False
PING_GOOGLE = True
PING_URL_ENCODED = 'http://www.google.com/webmasters/tools/ping?sitemap=http%3A%2F%2Fmediatum.ub.tum.de%2Fsitemap-index.xml'



class ConfigFile:

    """
    A configuration file object
    """

    def __init__(self, path, name):
        self.name = name
        self.path = '/'.join([path, self.name])
        self.parser = SafeConfigParser()
        self.host = None

    def get_hostname(self):
        """
        Attempts to parse the configuration file for the host value
        """
        if os.path.isfile(self.path):
            try:
                self.parser.read(self.path)
                self.host = self.parser.get('host', 'name')
            except IOError:
                logg.error('Error reading the configuration file %s', self.path)
        else:
            logg.error('The specified config file: %s does not exist', self.path)


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
            slashpattern = re.compile(r'\d{2}/\d{2}/\d{4}')
            datetimepattern = re.compile(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}')

            # check if date is already in the proper format
            matched = re.search(datetimepattern, date)
            if matched is not None:
                return date

            else:
                matched = re.search(slashpattern, date)
                if matched is not None:
                    timestruct = time.strptime(date, '%m/%d/%Y+%H:%M')
                    timedatetime = datetime.datetime.fromtimestamp(time.mktime(timestruct))
                    return ''.join([timedatetime.strftime('%Y-%m-%dT%H:%M:%S'), '+02:00'])
                else:
                    raise TypeError('unknown date format given: %s' % date)

        if os.path.isfile(self.path):
            logg.info('Sitemap already exists at %s', self.path)
        else:
            root = etree.Element('urlset', xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
            # Doesn't create a sitemap if no nodes to place in it
            if not nodes:
                pass
            else:
                for i in nodes:
                    url = etree.SubElement(root, 'url')
                    loc = etree.SubElement(url, 'loc')
                    if 'system.aliascol' in tree.getNode(i[0]).attributes and USE_ALIASES:
                        loc.text = ''.join(['http://', self.host, '/', tree.getNode(i[0]).attributes['system.aliascol']])
                    else:
                        loc.text = ''.join(['http://', self.host, '/node?id=', i[0]])
                    lastmod = etree.SubElement(url, 'lastmod')
                    if i[1] == '+02:00':
                        lastmod.text = ''.join([datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S'), i[1]])
                    else:
                        lastmod.text = check_date_format(i[1])
                    changefreq = etree.SubElement(url, 'changefreq')
                    changefreq.text = 'monthly'
                    priority = etree.SubElement(url, 'priority')
                    priority.text = p_num
                try:
                    with codecs.open(self.path, 'w', encoding='utf8') as f:
                        f.write('''<?xml version="1.0" encoding="UTF-8"?>\n''')
                        f.write(etree.tostring(root))
                except IOError:
                    logg.error('Error creating %s', self.path)

    def delete_sitemap(self):
        """
        Removes the sitemap from the directory structure /web/root/
        """
        if os.path.isfile(self.path):
            try:
                os.remove(self.path)
            except IOError:
                logg.error('Error removing %s', self.path)


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
            logg.info('%s already exists' % self.path)
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
                    with codecs.open(self.path, 'w', encoding='utf8') as f:
                        f.write('''<?xml version="1.0" encoding="UTF-8"?>\n''')
                        f.write(etree.tostring(root))
                except IOError:
                    logg.error('Error creating %s', self.path)

    def delete_sitemap_index(self):
        """
        Removes the sitemapindex from the directory structure /web/root/
        """
        if os.path.isfile(self.path):
            try:
                os.remove(self.path)
            except IOError:
                logg.error('Error removing %s', self.path)


def create():
    """
    Creates the sitemap files and the sitemap index files which are located at /web/root/
    """
    logg.info('Creating Sitemaps and Sitemap Index...')

    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))

    config = ConfigFile(base_dir, 'mediatum.cfg')
    config.get_hostname()

    if config.host is None:
        print 'The host was never set. \n Exiting process...'
        return
    else:
        hostname = config.host

    root = tree.getRoot('collections')
    all_nodes = root.getAllChildren()
    user = users.getUser('Gast')
    access = acl.AccessData(user=user)

    node_dict = {'collections': [],
                 'directories': [],
                 'documents': [],
                 'dissertations': [],
                 'images': [],
                 'videos': [],
                 'audio': [],
                 }
    sitemaps = []

    for i in all_nodes:
        # Arkitekt had a guest field that is actually not visible
        if access.hasAccess(i, 'read'):
            if 'collection' in tree.getNode(i.id).type:
                node_dict['collections'].append((i.id, '+'.join([tree.getNode(i.id).get('updatetime'), '02:00'])))
            elif 'directory' in tree.getNode(i.id).type:
                node_dict['directories'].append((i.id, '+'.join([tree.getNode(i.id).get('updatetime'), '02:00'])))
            elif 'document' in tree.getNode(i.id).type:
                node_dict['documents'].append((i.id, '+'.join([tree.getNode(i.id).get('updatetime'), '02:00'])))
            elif 'dissertation' in tree.getNode(i.id).type:
                node_dict['dissertations'].append((i.id, '+'.join([tree.getNode(i.id).get('updatetime'), '02:00'])))
            elif 'image' in tree.getNode(i.id).type:
                node_dict['images'].append((i.id, '+'.join([tree.getNode(i.id).get('updatetime'), '02:00'])))
            elif 'video' in tree.getNode(i.id).type:
                node_dict['videos'].append((i.id, '+'.join([tree.getNode(i.id).get('updatetime'), '02:00'])))
            elif 'audio' in tree.getNode(i.id).type:
                node_dict['audio'].append((i.id, '+'.join([tree.getNode(i.id).get('updatetime'), '02:00'])))

    # Reassign node_dict to a dict where empty values were removed
    node_dict = dict((k, v) for k, v in node_dict.iteritems() if v)

    # Sitemap can have at most 50k entries
    for i in node_dict.keys():
        if i is 'dissertations' or i is 'documents' or i is 'images':
            priority_level = '1.0'
        elif i is 'videos':
            priority_level = '0.8'
        else:
            priority_level = '0.5'

        # Create multiple sitemaps for node lists > 50k
        if len(node_dict[i]) > 50000:
            partitions = int(ceil((len(node_dict[i]) / 50000.)))
            for j in range(partitions):
                sitemap = Sitemap(base_dir, ''.join(['sitemap-', ustr(i), ustr(j), '.xml']), hostname)
                sitemaps.append(sitemap.name)
                sitemap.create_sitemap(node_dict[i][j * 50000:(j + 1) * 50000], priority_level)
        else:
            sitemap = Sitemap(base_dir, ''.join(['sitemap-', i, '.xml']), hostname)
            sitemaps.append(sitemap.name)
            sitemap.create_sitemap(node_dict[i], priority_level)

    siteindex = SitemapIndex(base_dir, 'sitemap-index.xml', hostname)
    now = '+'.join([datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S'), '02:00'])
    siteindex.create_sitemap_index(sitemaps, now)

    logg.info('Generation of Sitemaps and SitemapIndex Complete')


def clean():
    """
    Removes all .xml files from the /web/root/ directory
    """
    logg.info('Cleaning /root of all Sitemaps and SitemapIndex')

    base_dir = os.path.abspath(os.curdir)
    web_root_dir = '/'.join([base_dir, 'web', 'root'])

    sitemaps = [f for f in os.listdir(web_root_dir) if '.xml' in f and f.startswith('sitemap')]

    # If no .xml files exist
    if not sitemaps:
        logg.info('Nothing to remove...')
    else:
        for sm in sitemaps:
            logg.info('Deleting file: %s', sm)
            os.remove('/'.join([web_root_dir, sm]))

    logg.info('Cleaning Complete...')


def main():
    if len(sys.argv) > 2 or 'create' not in sys.argv and 'clean' not in sys.argv:
        raise TypeError('sitemap.py takes in only one of the following arguments: [create] [clean]')
    elif sys.argv[1] == 'create':
        clean()
        create()
        if PING_GOOGLE:
            response = urllib2.urlopen(PING_URL_ENCODED)
            if response.getcode() == 200:
                logg.info(
                    'Successful ping of sitemap-index.xml to Google; Response Code: %i', response.getcode())
            else:
                logg.info(
                    'Unsuccessful ping of sitemap-index.xml to Google; Response Code: %i', response.getcode())
    elif sys.argv[1] == 'clean':
        clean()

if __name__ == '__main__':
    main()
