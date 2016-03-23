# -*- coding: utf-8 -*-
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
import json
import logging
import os
from subprocess import CalledProcessError, check_call
import tempfile

from mediatumtal import tal
from contenttypes.data import Content
from contenttypes.image import makeThumbNail, makePresentationFormat
from core.transition.postgres import check_type_arg_with_schema
from core import db, File, config
from core.config import resolve_datadir_path
from core.translation import t
from core.styles import getContentStyles
from utils.utils import splitfilename
from utils.date import format_date, make_date


logg = logging.getLogger(__name__)


def getCaptionInfoDict(self):
    '''
        function should be reimplemented
        with the usage of the html5 Track element

        :return: captions dict / .srt format
    '''
    d = {}
    return d


@check_type_arg_with_schema
class Video(Content):

    @classmethod
    def get_original_filetype(cls):
        return "original"

    @classmethod
    def get_default_edit_menu_tabs(cls):
        return "menulayout(view);menumetadata(metadata;files;admin;lza);menuclasses(classes);menusecurity(acls)"

    @classmethod
    def get_sys_filetypes(cls):
        return [u"presentation", u"thumb", u"video"]

    def _prepareData(self, req, words=""):
        obj = super(Video, self)._prepareData(req)
        if obj["deleted"]:
            # no more processing needed if this object version has been deleted
            # rendering has been delegated to current version
            return obj

        # user must have data access for video playback
        if self.has_data_access():
            video = self.files.filter_by(filetype=u"video").scalar()
            obj["video_url"] = u"/file/{}/{}".format(self.id, video.base_name) if video is not None else None
        else:
            obj["video_url"] = None

        captions_info = getCaptionInfoDict(self)
        if captions_info:
            logg.debug("video: '%s' (%s): captions: dictionary 'captions_info': %s" % (self.name, str(self.id), str(captions_info)))

        obj["captions_info"] = json.dumps(captions_info)
        return obj

    def show_node_big(self, req, template="", macro=""):
        """Formats big view with standard template"""
        if template == "":
            styles = getContentStyles("bigview", contenttype=self.getContentType())
            if len(styles) >= 1:
                template = styles[0].getTemplate()

        context = self._prepareData(req)

        return tal.getTAL(template, context, macro)

    def show_node_image(self):
        """Returns preview image"""
        return '<img src="/thumbs/%s" class="thumbnail" border="0"/>' % self.id

    def event_files_changed(self):
        """Generates thumbnails (a small and a larger one) from a MP4 video file.
        The frame used as thumbnail can be changed by setting self.system_attrs["thumbframe"] to a number > 0.
        """
        video_file = self.files.filter_by(filetype=u"video").scalar()

        if video_file is not None:
            self.set('vid-width', self.get('width'))
            self.set('vid-height', self.get('height'))

            ffmpeg = config.get("external.ffmpeg", "ffmpeg")
            thumbframe = self.system_attrs.get("thumbframe")

            ffmpeg_call = [ffmpeg, "-y"]

            if thumbframe:
                ffmpeg_call += ['-ss', str(thumbframe)]  # change frame used as thumbnail

            ffmpeg_call += ['-i', video_file.abspath]  # input settings

            # Temporary file must be named and closed right after creation because ffmpeg wants to access it later.
            temp_thumbnail = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            try:
                temp_thumbnail.close()
                temp_thumbnail_path = temp_thumbnail.name
                ffmpeg_call += ['-vframes', '1', '-pix_fmt', 'rgb24', temp_thumbnail_path]  # output options

                try:
                    check_call(ffmpeg_call)
                except CalledProcessError:
                    logg.error("Error processing video, external call failed. No thumbnails generated.")
                    raise
                except OSError:
                    logg.error("Error processing video, external command ffmpeg cannot be called. No thumbnails generated.")
                    raise

                name_without_ext = os.path.splitext(video_file.path)[0]
                thumbname = u'{}.thumb'.format(name_without_ext)
                thumbname2 = u'{}.presentation'.format(name_without_ext)
                makeThumbNail(temp_thumbnail_path, resolve_datadir_path(thumbname))
                makePresentationFormat(temp_thumbnail_path, resolve_datadir_path(thumbname2))
            finally:
                os.unlink(temp_thumbnail_path)

            self.files.filter(File.filetype.in_([u'thumb', u'presentation'])).delete(synchronize_session=False)
            self.files.append(File(thumbname, u'thumb', u'image/jpeg'))
            self.files.append(File(thumbname2, u'presentation', u'image/jpeg'))

            db.session.commit()

    def getDuration(self):
        duration = self.get("duration")
        try:
            duration = float(duration)
        except ValueError:
            return 0
        else:
            return format_date(make_date(0, 0, 0, int(duration) / 3600, duration / 60, int(duration % 60)), '%H:%M:%S')

    def unwanted_attributes(self):
        '''
        Returns a list of unwanted attributes which are not to be extracted from uploaded videos
        @return: list
        '''
        return ['sourcedata',
                'httphostheader',
                'purl',
                'pmsg']

    """ list with technical attributes for type video """

    def getTechnAttributes(self):
        return {"Standard": {"creationtime": "Erstelldatum",
                             "creator": "Ersteller"},
                "FLV": {"audiodatarate": "Audio Datenrate",
                        "videodatarate": "Video Datenrate",
                        "framerate": "Frame Rate",
                        "height": u"Videohöhe",
                        "width": "Breite",
                        "audiocodecid": "Audio Codec",
                        "duration": "Dauer",
                        "canSeekToEnd": "Suchbar",
                        "videocodecid": "Video Codec",
                        "audiodelay": "Audioversatz"}
                }

    def processMediaFile(self, dest):
        for nfile in self.files:
            if nfile.filetype == "video":
                filename = nfile.abspath
                path, ext = splitfilename(filename)
                if os.sep == '/':
                    os.system("cp %s %s" % (filename, dest))
                else:
                    cmd = "copy %s %s%s.%s" % (filename, dest, self.id, ext)
                    os.system(cmd.replace('/', '\\'))
        return 1
