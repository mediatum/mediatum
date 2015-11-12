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

from utils.utils import splitfilename
from utils.date import format_date, make_date
from core.acl import AccessData
from core.tree import FileNode
from contenttypes.image import makeThumbNail, makePresentationFormat
from core.translation import lang, t
from core.styles import getContentStyles
from schema.schema import VIEW_HIDE_EMPTY
from metadata.upload import getFilelist
from utils.utils import getMimeType

from . import default


logger = logging.getLogger("backend")


def getCaptionInfoDict(self):
    d = {}

    file_url_list = []
    file_label_list = []
    preset_label = ""

    counter = 0

    filelist, filelist2 = getFilelist(self, fieldname='.*captions.*')

    for filenode in filelist2:
        if filenode.getType() in ["u_other", "u_xml"]:
            filename = filenode.getName()
            file_ext = filename.split('.')[-1]
            if file_ext in ['srt', 'xml']:
                counter += 1
                file_url = "/file/%s/%s" % (self.id, filename)
                file_url_list.append(file_url)

                x = filename[0:-len(file_ext) + 1].split('-')
                if len(x) > 1 and len(x[-1]):
                    file_label = x[-1]
                else:
                    file_label = "Track %s" % counter
                file_label_list.append(file_label)

                if filename.find('preset') >= 0:
                    preset_label = file_label

    if file_url_list:
        d['file_list'] = ",".join([x.strip() for x in file_url_list])
        d['label_list'] = ",".join([x.strip() for x in file_label_list])
        d['preset_label'] = preset_label
    return d


class Video(default.Default):

    """ video class """
    def getTypeAlias(self):
        return "video"

    def getOriginalTypeName(self):
        return "original"

    def getCategoryName(self):
        return "video"

    def _prepareData(self, req, words=""):

        access = acl.AccessData(req)
        mask = self.getFullView(lang(req))

        obj = {'deleted': False, 'access': access}
        node = self

        if len(node.getFiles()) == 0:
            obj['captions_info'] = {}
            obj['file'] = ''
            obj['hasFiles'] = False
            obj['hasVidFiles'] = False

        if len(node.getFiles()) > 0:
            obj['hasFiles'] = True
            if len([m for m in [getMimeType(os.path.abspath(f.retrieveFile()))[0].split('/')[0] for f in self.getFiles() if os.path.exists(os.path.abspath(f.retrieveFile()))] if m == 'video'])>0:
                obj['hasVidFiles'] = True
            else:
                obj['hasVidFiles'] = False

        if self.get('deleted') == 'true':
            node = self.getActiveVersion()
            obj['deleted'] = True
        for filenode in node.getFiles():
            if filenode.getType() in ["original", "video"]:
                obj["file"] = "/file/%s/%s" % (node.id, filenode.getName())

        if mask:
            obj['metadata'] = mask.getViewHTML([node], VIEW_HIDE_EMPTY, lang(req), mask=mask)  # hide empty elements
        else:
            obj['metadata'] = []
        obj['node'] = node
        obj['path'] = req.params.get("path", "")
        obj['canseeoriginal'] = access.hasAccess(node, "data")
        obj['parentInformation'] = self.getParentInformation(req)

        return obj

    """ format big view with standard template """
    def show_node_big(self, req, template="", macro=""):
        if len([f.retrieveFile() for f in self.getFiles()]) == 0:
            styles = getContentStyles("bigview", contenttype=self.getContentType())
            template = styles[0].getTemplate()
            return req.getTAL(template, self._prepareData(req), macro)

        if template == "":
            styles = getContentStyles("bigview", contenttype=self.getContentType())
            if len(styles) >= 1:
                template = styles[0].getTemplate()

        captions_info = getCaptionInfoDict(self)

        if captions_info:
            logger.info("video: '%s' (%s): captions: dictionary 'captions_info': %s" % (self.name, str(self.id), str(captions_info)))

        context = self._prepareData(req)
        context["captions_info"] = json.dumps(captions_info)

        if len([m for m in [getMimeType(os.path.abspath(f.retrieveFile()))[0].split('/')[0] for f in self.getFiles() if os.path.exists(os.path.abspath(f.retrieveFile()))] if m == 'video'])>0:
            return req.getTAL(template, context, macro)
        else:
            if len([th for th in [os.path.abspath(f.retrieveFile()) for f in self.getFiles()] if th.endswith('thumb2')])>0:
                return req.getTAL(template, context, macro)
            else:
                if len([f for f in self.getFiles() if f.getType() == 'attachment'])>0:
                    return req.getTAL(template, context, macro)

                return '<h2 style="width:100%; text-align:center ;color:red">Video is not in a supported video-format.</h2>'

    """ returns preview image """
    def show_node_image(self):
        return '<img src="/thumbs/%s" class="thumbnail" border="0"/>' % self.id

    def event_files_changed(self):
        for f in self.getFiles():
            if f.type in ["thumb", "presentation"]:
                self.removeFile(f)

        for f in self.getFiles():
            if f.mimetype == "video/mp4":
                for f in self.getFiles():
                    if f.type in ["thumb", "presentation"]:
                        self.removeFile(f)

                if len([f for f in self.getFiles() if f.mimetype == 'video/mp4']) > 0:
                    tempname = os.path.join(config.get("paths.tempdir"), "tmp.gif")

                    if os.path.exists(tempname):
                        os.remove(tempname)

                    mp4_path = f.retrieveFile()
                    mp4_name = os.path.splitext(mp4_path)[0]

                    try:
                        if self.get("system.thumbframe") != "":

                            cmd = "ffmpeg -loglevel quiet -ss {} -i {} -vframes 1 -pix_fmt rgb24 {}".format(self.get("system.thumbframe"), mp4_path, tempname)
                        else:
                            cmd = "ffmpeg -loglevel quiet -i {} -vframes 1 -pix_fmt rgb24 {}".format(mp4_path, tempname)
                        ret = os.system(cmd)
                        if ret & 0xff00:
                            return
                    except:
                        return
                    thumbname = "{}.thumb".format(mp4_name)
                    thumbname2 = "{}.thumb2".format(mp4_name)
                    makeThumbNail(tempname, thumbname)
                    makePresentationFormat(tempname, thumbname2)
                    self.addFile(FileNode(name=thumbname, type="thumb", mimetype="image/jpeg"))
                    self.addFile(FileNode(name=thumbname2, type="presentation", mimetype="image/jpeg"))

    def isContainer(self):
        return 0

    def getSysFiles(self):
        return ["presentation", "thumb", "video"]

    def getLabel(self):
        return self.name

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
                        "height": "Videoh\xc3\xb6he",
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

        access = AccessData(req)
        if not access.hasAccess(self, "data") or not access.hasAccess(self, "read"):
            req.write(t(req, "permission_denied"))
            return

        f = None
        for filenode in self.getFiles():
            if filenode.getType() in ["original", "video"] and filenode.retrieveFile().endswith('flv'):
                f = "/file/%s/%s" % (self.id, filenode.getName())
                break

        script = ""
        if f:
            script = '<p href="%s" style="display:block;width:%spx;height:%spx;" id="player"/p>' % (f, videowidth(), videoheight())

        # use jw player
        captions_info = getCaptionInfoDict(self)
        if captions_info:
            logger.info("video: '%s' (%s): captions: dictionary 'captions_info': %s" % (self.name, self.id, captions_info))

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
        for nfile in self.getFiles():
            if nfile.getType() == "video":
                filename = nfile.retrieveFile()
                path, ext = splitfilename(filename)
                if os.sep == '/':
                    os.system("cp %s %s" % (filename, dest))
                else:
                    cmd = "copy %s %s%s.%s" % (filename, dest, self.id, ext)
                    os.system(cmd.replace('/', '\\'))
        return 1
