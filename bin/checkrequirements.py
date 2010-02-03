#!/usr/bin/python
"""
 mediatum - a multimedia content repository

 Copyright (C) 2010 Arne Seifert <seiferta@in.tum.de>

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

from subprocess import Popen, PIPE

_modules = {}
print "-"*80, "\nCheck requred modules for the installation of mediatum"

print "\nCHECK DATABASES"

print " * MySQL (MySQL for Python):"
_modules['mysql'] = 0
try:
    import MySQLdb
    _modules['mysql'] = 1
except ImportError:
    pass
    
if _modules['mysql']==0:
    print "   -> no MySQL-Connector found."
else:
    print "   -> MySQL-Connector found."

print "\n * SqLite (sqlite3):"
_modules['sqlite'] = 0
try:
    import sqlite3
    _modules['sqlite'] = 1
except ImportError:
    try:
        import pysqlite2
        _modules['sqlite'] = 1
    except ImportError:
        pass
        
if _modules['sqlite']==0:
    print "   -> no SqLite-Connector found."
else:
    print "   -> SqLite-Connector found."

print "\nCHECK IMAGE LIB (Python Imaging Library)"
_modules['pil'] = 0

try:
    import Image
    _modules['pil'] = 1
except ImportError:
    pass
    
if _modules['pil']==0:
    print "   -> no Image Lib found."
else:
    print "   -> Image Lib found."
    
print "\nCHECK PDF-REPORTING LIB (ReportLab)"
_modules['reportlab'] = 0
try:
    import reportlab
    _modules['reportlab'] = 1
except ImportError:
    pass
    
if _modules['reportlab']==0:
    print "   -> no Report Lib found."
else:
    print "   -> Report Lib found."
    
print "\nCHECK EXTERNAL TOOLS:"
print " * Xpdf: pdfinfo to extract pdf meta information:"
_modules['pdfinfo'] = 0

try:
    c = Popen("pdfinfo -v", stdout=PIPE).communicate()
    _modules['pdfinfo'] = 1
except:
    pass
    
if _modules['pdfinfo']==0:
    print "   -> pdfinfo not found."
else:
    print "   -> pdfinfo found."

print "\n * Xpdf: pdftotext to extract pdf-text:"
_modules['pdftotext'] = 0

try:
    c = Popen("pdftotext -v", stdout=PIPE).communicate()
    _modules['pdftotext'] = 1
except:
    pass
    
if _modules['pdftotext']==0:
    print "   -> pdftotext not found."
else:
    print "   -> pdftotext found."
    
print "\n * ImageMagik: convert to extract pdf-text:"
_modules['convert'] = 0

try:
    c = Popen("convert", stdout=PIPE).communicate()
    _modules['convert'] = 1
except:
    pass
    
if _modules['convert']==0:
    print "   -> convert not found."
else:
    print "   -> convert found."
    
print "\n * ffmpeg to extract video thumbnails (flv):"
_modules['ffmpeg'] = 0

try:
    c = Popen("ffmpeg", stdout=PIPE).communicate()
    _modules['ffmpeg'] = 1
except:
    pass
    
if _modules['ffmpeg']==0:
    print "   -> ffmpeg not found."
else:
    print "   -> ffmpeg found."
    
x=0
for k in _modules:
    x += _modules[k]

if x!=len(_modules.keys()):
    print "\n-> there are some important modules missing."
else:
    print "\n-> all needed modules found."
   
print "-"*80