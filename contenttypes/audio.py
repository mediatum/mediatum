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
import shutil
from PIL import Image, ImageDraw
from contenttypes.data import Content, prepare_node_data
from lib.audio import File as AudioFile
from utils.utils import splitfilename
from utils.date import parse_date, format_date, make_date
from schema.schema import VIEW_HIDE_EMPTY
from core.translation import lang
from core.transition.postgres import check_type_arg_with_schema
from core import File
from core import db
import utils.process

logg = logging.getLogger(__name__)


def makeAudioThumb(self, audiofile):
    ret = None
    path, ext = splitfilename(audiofile.abspath)
    if not audiofile.abspath.endswith(".mp3"):
        ret = path + ".mp3"
        utils.process.call(("lame", "-V", "4", "-q", audiofile.abspath, ret))
    self.files.append(File(path + ".mp3", "mp3", "audio/mpeg"))
    return ret

# """ make thumbnail (jpeg 128x128) """


def make_thumbnail_image(self, audiofile):
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

                self.files.append(File(path + ".thumb", "thumb", audiofile.tags[k].mime))
                break


# """ make presentation format (jpeg 320x320) """
def convert_image(self, audiofile):
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
                self.files.append(File(path + ".thumb2", "presentation", audiofile.tags[k].mime))
                break


def makeMetaData(self, audiofile):
    self.attrs["mp3.version"] = audiofile.info.version
    self.attrs["mp3.layer"] = audiofile.info.layer
    self.attrs["mp3.bitrate"] = u"{} kBit/s".format(audiofile.info.bitrate / 1000)
    self.attrs["mp3.sample_rate"] = u"{} kHz".format(audiofile.info.sample_rate / 1000)

    _s = int(audiofile.info.length % 60)
    _m = audiofile.info.length / 60
    _h = int(audiofile.info.length) / 3600

    self.attrs["mp3.length"] = format_date(make_date(0, 0, 0, _h, _m, _s), '%Y-%m-%dT%H:%M:%S')

    if audiofile.tags:
        for key in audio_frames.keys():
            if key in audiofile.tags.keys():
                self.attrs["mp3." + audio_frames[key]] = unicode(audiofile.tags[key])


@check_type_arg_with_schema
class Audio(Content):

    @classmethod
    def get_sys_filetypes(cls):
        return [u"audio", u"thumb", u"presentation", u"mp3"]

    @classmethod
    def get_default_edit_menu_tabs(cls):
        return "menulayout(view);menumetadata(metadata;files;admin;lza);menuclasses(classes);menusecurity(acls)"

    # prepare hash table with values for TAL-template
    def _prepareData(self, req):
        obj = prepare_node_data(self, req)
        if obj["deleted"]:
            # no more processing needed if this object version has been deleted
            # rendering has been delegated to current version
            return obj

        node = self

        # adapted from video.py
        # user must have data access for audio playback
        if self.has_data_access():
            audio_file = self.files.filter_by(filetype=u"audio").scalar()
            obj["audio_url"] = u"/file/{}/{}".format(self.id, audio_file.base_name) if audio_file is not None else None
            versions = self.tagged_versions.all()
            obj['tag'] = versions[-1].tag if len(versions) > 1 else None
            if not self.isActiveVersion():
                obj['audio_url'] += "?v=" + self.tag

            if node.isActiveVersion():
                if node.system_attrs.get('origname') == "1":
                    obj['audiodownload'] = u'/download/{}/{}'.format(node.id, node.name)
                else:
                    obj['audiodownload'] = u'/download/{}/{}.mp3'.format(node.id, node.id)
            else:
                    obj['audiodownload'] += "?v=" + node.tag

        else:
            obj["audio_url"] = None

        return obj

    def has_object(self):
        for f in self.files:
            if f.type == "audio":
                return True
        return False

    """ postprocess method for object type 'audio'. called after object creation """
    def event_files_changed(self):
        logg.debug("Postprocessing node %s", self.id)

        original = None
        audiothumb = None
        thumb = None
        thumb2 = None

        for f in self.files:
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
                self.files.remove(audiothumb)
            if thumb:  # delete old thumb
                self.files.remove(thumb)
            if thumb2:  # delete old thumb2
                self.files.remove(thumb2)

            athumb = makeAudioThumb(self, original)
            if athumb:
                _original = AudioFile(athumb)
            else:
                _original = AudioFile(original.abspath)
            convert_image(self, _original)
            make_thumbnail_image(self, _original)
            makeMetaData(self, _original)

        db.session.commit()

    """ list with technical attributes for type image """
    def getTechnAttributes(self):
        return {}

    def getDuration(self):
        return format_date(parse_date(self.get("mp3.length")), '%H:%M:%S')

    def processMediaFile(self, dest):
        for file in self.files:
            if file.getType() == "audio":
                filename = file.abspath
                path, ext = splitfilename(filename)
                try:
                    shutil.copy(filename, dest)
                except:
                    logg.exception("file copy")
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
