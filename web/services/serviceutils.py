"""
 mediatum - a multimedia content repository

 Copyright (C) 2007 Arne Seifert <seiferta@in.tum.de>
 Copyright (C) 2007 Matthias Kramm <kramm@in.tum.de>
 Copyright (C) 2011 Werner F. Neudenberger <neudenberger@ub.tum.de>

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

import unicodedata

# Sorting:

def normchar(char_descriptor):
    return unicodedata.lookup(char_descriptor).encode("utf-8").lower()

# data source:
# http://www.w3.org/TR/2008/WD-xml-entity-names-20080721/bycodes.html

# http://de.wikipedia.org/wiki/Alphabetische_Sortierung :
# DIN 5700 Variant 1: Sorting words: auml = a, ...
# DIN 5700 Variant 2: Sorting names: auml = ae, ...
# Remark: Austrian sorting in some cases: auml after az

din5007_variant1_translation = [
 [normchar('LATIN CAPITAL LETTER A WITH DIAERESIS'), 'a'],  # Auml
 [normchar('LATIN CAPITAL LETTER O WITH DIAERESIS'), 'o'],  # Ouml
 [normchar('LATIN CAPITAL LETTER U WITH DIAERESIS'), 'u'],  # Uuml
 [normchar('LATIN SMALL LETTER A WITH DIAERESIS'), 'a'],  # auml
 [normchar('LATIN SMALL LETTER O WITH DIAERESIS'), 'o'],  # ouml
 [normchar('LATIN SMALL LETTER U WITH DIAERESIS'), 'u'],  # uuml
 [normchar('LATIN SMALL LETTER SHARP S'), 'ss'],  # szlig
 [normchar('LATIN SMALL LETTER E WITH GRAVE'), 'e'],  # egrave 
 [normchar('LATIN SMALL LETTER E WITH ACUTE'), 'e'],  # eacute
]

din5007_variant2_translation = [
 [normchar('LATIN CAPITAL LETTER A WITH DIAERESIS'), 'ae'],  # Auml
 [normchar('LATIN CAPITAL LETTER O WITH DIAERESIS'), 'oe'],  # Ouml
 [normchar('LATIN CAPITAL LETTER U WITH DIAERESIS'), 'ue'],  # Uuml
 [normchar('LATIN SMALL LETTER A WITH DIAERESIS'), 'ae'],  # auml
 [normchar('LATIN SMALL LETTER O WITH DIAERESIS'), 'oe'],  # ouml
 [normchar('LATIN SMALL LETTER U WITH DIAERESIS'), 'ue'],  # uuml
 [normchar('LATIN SMALL LETTER SHARP S'), 'ss'],  # szlig
 [normchar('LATIN SMALL LETTER E WITH GRAVE'), 'e'],  # egrave 
 [normchar('LATIN SMALL LETTER E WITH ACUTE'), 'e'],  # eacute
]

def sortkey_translation(input_value, translation):
    '''make sort key'''
    try: 
        key = input_value.lower()
        for src, dest in translation:
            key = key.replace(src, dest)
        return key
    except:
        # i.e. number
        return input_value 

def din5007v1(input_value):
    '''make sort key din5007 variant 1'''
    return sortkey_translation(input_value, din5007_variant1_translation)

def din5007v2(input_value):
    '''make sort key din5007 variant 2'''
    return sortkey_translation(input_value, din5007_variant2_translation)

def attribute_name_filter(attribute_name):
    '''filter out node attributes that should not be served'''
    if attribute_name.startswith("system."):
        return False
    return True    