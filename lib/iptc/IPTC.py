#!/usr/bin/python
# Python IPTC Parser
# By Jean-Francois Roche <jfroche@jfroche.be>
# ZPhotoSlides, Zope product
# Copyright (C) 2002-2004  Jean-Francois Roche <jfroche@jfroche.be>
#                          Florent Carlier <florent.carlier@insa-rennes.fr>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
# $Id: IPTC.py,v 1.1 2007/09/05 09:48:23 kramm Exp $'
# Based on a PHP script for IPTC parser this avoid to install PIL
import sys
from StringIO import StringIO



TagsNames = {
        0x14 : 'SuplementalCategories',
        0x19 : 'Keywords',
        0x78 : 'Caption',
        0x7A: 'CaptionWriter',
        0x69: 'Headline',
        0x28: 'SpecialInstructions',
        0x0F: 'Category',
        0x50: 'Byline',
        0x55: 'BylineTitle',
        0x6E: 'Credit',
        0x73: 'Source',
        0x74: 'CopyrightNotice',
        0x05: 'ObjectName',
        0x5A: 'City',
        0x5F: 'ProvinceState',
        0x65: 'CountryName',
        0x67: 'OriginalTransmissionReference',
        0x37: 'DateCreated',
        0x0A: 'CopyrightFlag'
        }

try:
    f = False
except:
    False = -1
    True = 1

def i16(c,o=0):
        return ord(c[o+1]) + (ord(c[o])<<8)

def i32(c,o=0):
        return ord(c[o+3]) + (ord(c[o+2])<<8) + (ord(c[o+1])<<16) + (ord(c[o])<<24)


def getiptc_path(path):
    file = open(path,'rb')
    return getiptc(file)
def getiptc_data(data):
    return getiptc(StringIO(data))

def getiptc(file):
    data=file.read(1)
    if(ord(data)!=0xFF):
        print "1"
        return {}
    data=file.read(1)
    if(ord(data)!=0xD8):
        print "2"
        return {}
    count = 0
    done = False
    ok = True
    _markers = {}
    while(not done):
        capture = False
        discarded = 0
        c = ord(file.read(1))
        while(c!=0xFF):
            discarded = discarded +1
            c = ord(file.read(1))
        marker = ord(file.read(1))
        while(marker==0xFF):
            marker = ord(file.read(1))
        if (discarded != 0):
            break
        length = (ord(file.read(1))*256 + ord(file.read(1)))
        if (length < 2):
            break

        if(marker == 0xC0 or marker == 0xC1 or marker == 0xC2 or marker == 0xC9 or marker==0xE0 or marker==0xE1):
            pass #dont care about them
        elif(marker == 0xED):    # SOF1
            capture = True
            done = True
        elif(marker == 0xDA):  # SOS: Start of scan... the image itself and the last block on the file
            capture = False
            length = -1  # This field has no length... it includes all data until EOF
            done = True
        else:
            capture = True
        _markers[count] = {}
        _markers[count]['marker'] = marker
        _markers[count]['length'] = length
        if (capture):
            _markers[count]['data'] = file.read(length)
        elif (not done):#result = @fseek($this->_fp, $length, SEEK_CUR);
            file.seek(length-2,1)
        count = count+1

    data = 0
    for key in _markers.keys():
        dict = _markers[key]
        if(dict['marker']==0xED):
            tmpdata = StringIO(dict['data'])
            signature = tmpdata.read(14)
            if(signature=="Photoshop 3.0\0"):
                data = dict['data']
                break
    if (data == 0):
        print "3"
        return {}
    pos = 14
    datasize = len(data)
    _markers['iptc'] = {}
    while (pos < datasize):
        signature = data[pos:pos+4]
        if (signature != '8BIM'):
            break
        pos = pos + 4
        types = i16(data,pos)
        pos = pos + 2
        strlen = ord(data[pos])
        pos = pos+1
        header = data[pos:pos+strlen]
        pos = pos+ strlen + 1 - (strlen % 2)  # The string is padded to even length, counting the length byte 
        length = i32(data,pos)
        pos = pos+ 4
        basePos = pos
        if(types==0x404):
            #we have iptc here!
            while (pos < (datasize - 5)):
                signature = i16(data,pos)
                if (signature != 0x1C02):
                    break
                pos = pos+ 2
                types = ord(data[pos])
                pos = pos+ 1
                length = i16(data,pos)
                pos = pos +2
                basePos = pos
                label = ''
                if (TagsNames.has_key(types)):
                    label = TagsNames[types]
                else:
                    label = 'IPTC_%s' % types
                if(_markers['iptc'].has_key(label)):
                    if(type(_markers['iptc'][label])!=type([])):
                        tmp = _markers['iptc'][label]
                        _markers['iptc'][label] = []
                        _markers['iptc'][label].append(tmp)
                    _markers['iptc'][label].append(data[pos:pos+length])
                else:
                    _markers['iptc'][label] = data[pos:pos+length]
                pos = basePos + length
    return _markers['iptc']

def getIPTCValues(filename):
    print filename
    return getiptc_path(filename)
