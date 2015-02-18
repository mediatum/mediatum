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

import logging
import os
import codecs
from PIL import Image, ImageDraw
from . import default
import core.acl as acl
from lib.audio import File as AudioFile
from utils.utils import splitfilename
from core.tree import FileNode
from utils.date import parse_date, format_date, make_date
from schema.schema import VIEW_HIDE_EMPTY
from core.translation import lang
from core.styles import getContentStyles


logg = logging.getLogger(__name__)


def makeAudioThumb(self, audiofile):
    ret = None
    path, ext = splitfilename(audiofile.retrieveFile())
    if not audiofile.retrieveFile().endswith(".mp3"):
        os.system("lame -V 4 -q %s %s" % (audiofile.retrieveFile(), path + ".mp3"))
        ret = path + ".mp3"
    self.addFile(FileNode(name=path + ".mp3", type="mp3", mimetype="audio/mpeg"))
    return ret

# """ make thumbnail (jpeg 128x128) """


def makeThumbNail(self, audiofile):
    path, ext = splitfilename(audiofile.filename)

    if audiofile.tags:
        for k in audiofile.tags:
            if k == "APIC:thumbnail":
                with open("{}.thumb".format(path), "wb") as fout:
                    fout.write(audiofile.tags[k].data)

                pic = Image.open(path + ".thumb2")
                width = pic.size[0]
                height = pic.size[1]

                if width > height:
                    newwidth = 128
                    newheight = height * newwidth / width
                else:
                    newheight = 128
                    newwidth = width * newheight / height
                pic = pic.resize((newwidth, newheight), Image.ANTIALIAS)
                pic.save(path + ".thumb", "jpeg")
                pic = pic.resize((newwidth, newheight), Image.ANTIALIAS)
                im = Image.new(pic.mode, (128, 128), (255, 255, 255))

                x = (128 - newwidth) / 2
                y = (128 - newheight) / 2
                im.paste(pic, (x, y, x + newwidth, y + newheight))

                draw = ImageDraw.ImageDraw(im)
                draw.line([(0, 0), (127, 0), (127, 127), (0, 127), (0, 0)], (128, 128, 128))

                im = im.convert("RGB")
                im.save(path + ".thumb", "jpeg")

                self.addFile(FileNode(name=path + ".thumb", type="thumb", mimetype=audiofile.tags[k].mime))
                break


# """ make presentation format (jpeg 320x320) """
def makePresentationFormat(self, audiofile):
    path, ext = splitfilename(audiofile.filename)

    if audiofile.tags:
        for k in audiofile.tags:
            if k == "APIC:thumbnail":
                with open("{}.thumb2".format(path), "wb") as fout:
                    fout.write(audiofile.tags[k].data)

                pic = Image.open(path + ".thumb2")
                width = pic.size[0]
                height = pic.size[1]

                if width > height:
                    newwidth = 320
                    newheight = height * newwidth / width
                else:
                    newheight = 320
                    newwidth = width * newheight / height
                pic = pic.resize((newwidth, newheight), Image.ANTIALIAS)
                pic.save(path + ".thumb2", "jpeg")
                self.addFile(FileNode(name=path + ".thumb2", type="presentation", mimetype=audiofile.tags[k].mime))
                break


def makeMetaData(self, audiofile):
    self.set("mp3.version", audiofile.info.version)
    self.set("mp3.layer", audiofile.info.layer)
    self.set("mp3.bitrate", unicode(int(audiofile.info.bitrate) / 1000) + " kBit/s")
    self.set("mp3.sample_rate", unicode(float(audiofile.info.sample_rate) / 1000) + " kHz")

    _s = int(audiofile.info.length % 60)
    _m = audiofile.info.length / 60
    _h = int(audiofile.info.length) / 3600

    self.set("mp3.length", format_date(make_date(0, 0, 0, _h, _m, _s), '%Y-%m-%dT%H:%M:%S'))

    if audiofile.tags:
        for key in audio_frames.keys():
            if key in audiofile.tags.keys():
                self.set("mp3." + audio_frames[key], audiofile.tags[key])


""" audio class for internal audio-type """


class Audio(default.Default):

    def getTypeAlias(self):
        return "audio"

    def getOriginalTypeName(self):
        return "original"

    def getCategoryName(self):
        return "audio"

    # prepare hash table with values for TAL-template
    def _prepareData(self, req):
        access = acl.AccessData(req)
        mask = self.getFullView(lang(req))

        obj = {'deleted': False, 'access': access}
        node = self
        if self.get('deleted') == 'true':
            node = self.getActiveVersion()
            obj['deleted'] = True
        if mask:
            obj['metadata'] = mask.getViewHTML([node], VIEW_HIDE_EMPTY, lang(req), mask=mask)  # hide empty elements
        else:
            obj['metadata'] = []
        obj['node'] = node
        obj['path'] = req and req.params.get("path", "") or ""
        obj['audiothumb'] = u'/thumb2/{}'.format(node.id)
        if node.has_object():
            obj['canseeoriginal'] = access.hasAccess(node, "data")
            obj['audiolink'] = u'/file/{}/{}'.format(node.id, node.getName())
            obj['audiodownload'] = u'/download/{}/{}'.format(node.id, node.getName())
        else:
            obj['canseeoriginal'] = False

        return obj

    """ format big view with standard template """
    def show_node_big(self, req, template="", macro=""):
        if template == "":
            styles = getContentStyles("bigview", contenttype=self.getContentType())
            if len(styles) >= 1:
                template = styles[0].getTemplate()
        return req.getTAL(template, self._prepareData(req), macro)

    def isContainer(self):
        return 0

    def getLabel(self):
        return self.name

    def has_object(self):
        for f in self.getFiles():
            if f.type == "audio":
                return True
        return False

    def getSysFiles(self):
        return ["audio", "thumb", "presentation", "mp3"]

    """ postprocess method for object type 'audio'. called after object creation """
    def event_files_changed(self):
        logg.debug("Postprocessing node %s", self.id)

        original = None
        audiothumb = None
        thumb = None
        thumb2 = None

        for f in self.getFiles():
            if f.type == "audio":
                original = f
            if f.type == "mp3":
                audiothumb = f
            if f.type.startswith("present"):
                thumb2 = f
            if f.type == "thumb":
                thumb = f

        if original:

            if audiothumb:
                self.removeFile(audiothumb)
            if thumb:  # delete old thumb
                self.removeFile(thumb)
            if thumb2:  # delete old thumb2
                self.removeFile(thumb2)

            athumb = makeAudioThumb(self, original)
            if athumb:
                _original = AudioFile(athumb)
            else:
                _original = AudioFile(original.retrieveFile())
            makePresentationFormat(self, _original)
            makeThumbNail(self, _original)
            makeMetaData(self, _original)

    """ list with technical attributes for type image """
    def getTechnAttributes(self):
        return {}

    def getDuration(self):
        return format_date(parse_date(self.get("mp3.length")), '%H:%M:%S')

    def getEditMenuTabs(self):
        return "menulayout(view);menumetadata(metadata;files;admin;lza);menuclasses(classes);menusecurity(acls)"

    def getDefaultEditTab(self):
        return "view"

    def processMediaFile(self, dest):
        for file in self.getFiles():
            if file.getType() == "audio":
                filename = file.retrieveFile()
                path, ext = splitfilename(filename)
                if os.sep == '/':
                    ret = os.system("cp %s %s" % (filename, dest))
                else:
                    cmd = "copy %s %s%s.%s" % (filename, dest, self.id, ext)
                    ret = os.system(cmd.replace('/', '\\'))
        return 1


audio_frames = {"AENC": "audio_encryption",
                "APIC": "attached_picture",
                "COMM": "comments",
                "COMR": "commercial_frame",
                "ENCR": "encryption_method_registration",
                "EQUA": "equalization",
                "ETCO": "event_timing_codes",
                "GEOB": "general_encapsulated_object",
                "GRID": "group_identification_registration",
                "IPLS": "involved_people_list",
                "LINK": "linked_information",
                "MCDI": "music_cd_dentifier",
                "MLLT": "mpeg_location_lookup_table",
                "OWNE": "ownership_frame",
                "PRIV": "private_frame",
                "PCNT": "play_counter",
                "POPM": "popularimeter",
                "POSS": "position_synchronisation_frame",
                "RBUF": "recommended_buffer_size",
                "RVAD": "relative_volume_adjustment",
                "RVRB": "reverb",
                "SYLT": "synchronized_lyric_text",
                "SYTC": "synchronized_tempo_codes",
                "TALB": "album_title",
                "TBPM": "bpm",
                "COM ": "composer",
                "TCON": "genre",
                "TCOP": "copyright_message",
                "TDAT": "date",
                "TDLY": "playlist_delay",
                "TENC": "encoded_by",
                "TEXT": "text_writer",
                "TFLT": "file_type",
                "TIME": "time",
                "TIT1": "content_group_description",
                "TIT2": "title",
                "TIT3": "subtitle",
                "TKEY": "initial_key",
                "TLAN": "language",
                "TLEN": "length",
                "TMED": "media_type",
                "TOAL": "original_album_title",
                "TOFN": "original_filename",
                "TOLY": "original_lyricist_writer",
                "TOPE": "original_artist",
                "TORY": "original_release_year",
                "TOWN": "file_owner",
                "TPE1": "performer",
                "TPE2": "band",
                "TPE3": "conductor",
                "TPE4": "interpreted_by",
                "TPOS": "part_of_set",
                "TPUB": "publisher",
                "TRCK": "track",
                "TRDA": "recording_dates",
                "TRSN": "internet_station_name",
                "TRSO": "internet_station_owner",
                "TSIZ": "size",
                "TSRC": "isrc",
                "TSSE": "encoding_settings",
                "TYER": "year",
                "TXXX": "user_text",
                "UFID": "file_identifier",
                "USER": "terms_of_use",
                "USLT": "unsychronized_text_transcription",
                "WCOM": "commercial_information",
                "WCOP": "copyright_information",
                "WOAF": "audio_webpage",
                "WOAR": "artist_webpage",
                "WOAS": "source_webpage",
                "WORS": "radio_homepage",
                "WPAY": "payment",
                "WPUB": "publishers_webpage",
                "WXXX": "user_defined_url"}
