"""
 mediatum - a multimedia content repository

 Copyright (C) 2007 Arne Seifert <seiferta@in.tum.de>
 Copyright (C) 2007 Matthias Kramm <kramm@in.tum.de>
 Copyright (C) 2012 Peter Heckl <heckl@ub.tum.de>

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


chkmap = {
"0":  "1", "1":  "2", "2":  "3", "3":  "4", "4":  "5", "5":  "6", "6":  "7", "7":  "8",
"8":  "9", "9": "41", "a": "18", "b": "14", "c": "19", "d": "15", "e": "16", "f": "21",
"g": "22", "h": "23", "i": "24", "j": "25", "k": "42", "l": "26", "m": "27", "n": "13",
"o": "28", "p": "29", "q": "31", "r": "12", "s": "32", "t": "33", "u": "11", "v": "34",
"w": "35", "x": "36", "y": "37", "z": "38", "-": "39", ":": "17"}

def buildChecksum(urn):
    i = 1
    digit = "0"
    sum = 0
    for char in urn: 
        for digit in chkmap.get(char,""):
            sum += int(digit)*i
            i = i + 1
    return str(sum / int(digit))[-1:]

def buildNBN(snid1,snid2,niss):
    urn = "urn:nbn:de:"+str(snid1)+":"+str(snid2)+"-"+niss+"-"
    return urn+buildChecksum(urn)

def increaseURN(urn):
    if urn.startswith("urn:nbn"):
        # nbn urns have a checksum digit at the end
        checksum = 1
        urn = urn[0:-1]
    dashes = 0
    while urn.endswith("-"):
        dashes = dashes + 1
        urn = urn[:-1]
    # increate the urn, starting with the last number
    i = len(urn)-1
    add1 = 1
    while add1:
        add1 = 0
        if i>=0 and ord('0')<=ord(urn[i])<=ord('9'):
            newnr = ord(urn[i])+1
            if newnr > ord('9'):
                add1 = 1
                newnr = ord('0')
            urn = urn[0:i]+chr(newnr)+urn[i+1:]
        else:
            urn = urn[0:i+1]+'0'+urn[i+1:]
        i = i - 1
    urn += "-"*dashes
    if checksum:
        # re-add checksum digit
        urn += buildChecksum(urn)
    return urn

def checkURN(urn):
    if not urn.startswith("urn"):
        return "doesn't start with 'urn'"
    if urn.lower() != urn:
        return "is not all lowercase"
    if buildChecksum(urn[:-1]) != urn[-1:]:
        return "check sum of '"+urn[:-1]+"' is '"+urn[-1:]+"' but should be '"+buildChecksum(urn[:-1])+"'"
    return # ok

