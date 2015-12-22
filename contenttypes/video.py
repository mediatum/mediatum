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
import core.config as config
import core.acl as acl
import os
import json
import logging
import subprocess

from utils.utils import splitfilename
from utils.date import format_date, make_date
from lib.flv.parse import FLVReader
from contenttypes.image import makeThumbNail, makePresentationFormat
from core.translation import lang, t
from core.styles import getContentStyles
from schema.schema import VIEW_HIDE_EMPTY
from metadata.upload import getFilelist
from contenttypes.data import Content
from core.transition.postgres import check_type_arg_with_schema
from core import db
from core import File
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

    """ video class """
    @classmethod
    def getTypeAlias(cls):
        return "video"

    @classmethod
    def getOriginalTypeName(cls):
        return "original"

    @classmethod
    def getCategoryName(cls):
        return "video"

    def _prepareData(self, req, words=""):
        mask = self.getFullView(lang(req))

        obj = {'deleted': False}
        node = self

        if len(node.files) == 0:
            obj['captions_info'] = {}
            obj['file'] = ''
            obj['hasFiles'] = False
            obj['hasVidFiles'] = False

        if len(node.files) > 0:
            obj['hasFiles'] = True

            if len([f for f in self.files if os.path.exists('{}/{}'.format(os.path.abspath(config.get('paths.datadir')), f.path)) and f.type == 'video']) > 0:
                obj['hasVidFiles'] = True
            else:
                obj['hasVidFiles'] = False

        if self.get('deleted') == 'true':
            node = self.getActiveVersion()
            obj['deleted'] = True
        for filenode in node.files:
            if filenode.filetype in ["original", "video"]:
                obj["file"] = "/file/%s/%s" % (node.id, filenode.base_name)
                break

        if mask:
            obj['metadata'] = mask.getViewHTML([node], VIEW_HIDE_EMPTY, lang(req), mask=mask)  # hide empty elements
        else:
            obj['metadata'] = []
        obj['node'] = node
        obj['path'] = req.params.get("path", "")
        obj['canseeoriginal'] = node.has_data_access()

        obj['parentInformation'] = self.getParentInformation(req)

        return obj

    """ format big view with standard template """
    def show_node_big(self, req, template="", macro=""):
        if len([f.path for f in self.files]) == 0:
            styles = getContentStyles("bigview", contenttype=self.getContentType())
            template = styles[0].getTemplate()
            return req.getTAL(template, self._prepareData(req), macro)

        if template == "":
            styles = getContentStyles("bigview", contenttype=self.getContentType())
            if len(styles) >= 1:
                template = styles[0].getTemplate()

        captions_info = getCaptionInfoDict(self)

        if captions_info:
            logg.info("video: '%s' (%s): captions: dictionary 'captions_info': %s" % (self.name, str(self.id), str(captions_info)))

        context = self._prepareData(req)
        context["captions_info"] = json.dumps(captions_info)

        if len([m for m in [f.type for f in self.files if os.path.exists(os.path.abspath(f.path))] if m == 'video']) > 0:
            return req.getTAL(template, context, macro)
        else:
            if len([th for th in [os.path.abspath(f.path) for f in self.files] if th.endswith('thumb2')]) > 0:
                return req.getTAL(template, context, macro)
            else:
                if len([f for f in self.files if f.type == 'attachment']) > 0:
                    return req.getTAL(template, context, macro)

                return '<h2 style="width:100%; text-align:center ;color:red">Video is not in a supported video-format.</h2>'

    """ returns preview image """
    def show_node_image(self):
        return '<img src="/thumbs/%s" class="thumbnail" border="0"/>' % self.id

    def event_files_changed(self):
        for f in self.files:
            if f.type in ['thumb', 'thumb2', 'presentation']:
                self.files.remove(f)
                db.session.commit()

            if f.mimetype == 'video/mp4':
                if len([f for f in self.files if f.mimetype == 'video/mp4']) > 0:
                    if f.type == 'video':
                        tempname = os.path.join(config.get('paths.tempdir'), 'tmp.gif')

                        self.set('vid-width', self.get('width'))
                        self.set('vid-height', self.get('height'))

                        if os.path.exists(tempname):
                            os.remove(tempname)

                        mp4_path = '{}/{}'.format(os.path.abspath(config.get('paths.datadir')), f.path)
                        mp4_name = os.path.splitext(mp4_path)[0]

                        try:
                            if self.get("system.thumbframe") != '':
                                ret = subprocess.call(['ffmpeg',  '-y', '-ss', '{}'.format(self.get('system.thumbframe')), '-i', '{}'.format(mp4_path), '-vframes', '1', '-pix_fmt', 'rgb24', '{}'.format(tempname)]) #'-loglevel', 'quiet',
                            else:
                                ret = subprocess.call(['ffmpeg',  '-y', '-i', '{}'.format(mp4_path), '-vf', 'thumbnail', '-frames:v', '1', '-pix_fmt', 'rgb24', '{}'.format(tempname)]) #'-loglevel', 'quiet',
                        except:
                            return

                        thumbname = '{}.thumb'.format(mp4_name)
                        thumbname2 = '{}.thumb2'.format(mp4_name)
                        makeThumbNail(tempname, thumbname)
                        makePresentationFormat(tempname, thumbname2)

                        self.files.append(File(thumbname, 'thumb', 'image/jpeg'))
                        self.files.append(File(thumbname2, 'thumb2', 'image/jpeg'))

                        db.session.commit()

    @classmethod
    def isContainer(cls):
        return 0

    def getSysFiles(self):
        return [u"presentation", u"thumb", u"video"]

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

    """ popup window for actual nodetype """
    def popup_fullsize(self, req):

        def videowidth():
            return int(self.get('vid-width') or 0) + 64

        def videoheight():
            int(self.get('vid-height') or 0) + 53

        if not self.has_data_access() or not self.has_read_access():
            req.write(t(req, "permission_denied"))
            return

        f = None
        for filenode in self.files:
            if filenode.filetype in ["original", "video"] and filenode.abspath.endswith('flv'):
                f = "/file/%s/%s" % (self.id, filenode.base_name)
                break

        script = ""
        if f:
            script = '<p href="%s" style="display:block;width:%spx;height:%spx;" id="player"/p>' % (f, videowidth(), videoheight())

        # implement html5 track element
        captions_info = getCaptionInfoDict(self)
        if captions_info:
            logg.info("video: '%s' (%s): captions: dictionary 'captions_info': %s", self.name, self.id, captions_info)

        context = {
            "file": f,
            "script": script,
            "node": self,
            "width": videowidth(),
            "height": videoheight(),
            "captions_info": json.dumps(captions_info),
        }

        req.writeTAL("contenttypes/video.html", context, macro="fullsize_flv_jwplayer")

    def popup_thumbbig(self, req):
        self.popup_fullsize(req)

    def getEditMenuTabs(self):
        return "menulayout(view);menumetadata(metadata;files;admin;lza);menuclasses(classes);menusecurity(acls)"

    def getDefaultEditTab(self):
        return "view"

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
