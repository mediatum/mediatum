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

import os
import core
import core.tree as tree
import default
import core.acl as acl
from lib.audio import File as AudioFile
from utils.utils import splitfilename
from core.tree import FileNode
from utils.date import parse_date, format_date, make_date
from schema.schema import loadTypesFromDB, VIEW_HIDE_EMPTY,VIEW_DATA_ONLY
from core.translation import lang, t
from core.styles import getContentStyles

def makeAudioThumb(node, audiofile):
    ret = None
    path, ext = splitfilename(audiofile.retrieveFile())
    if not audiofile.retrieveFile().endswith(".mp3"):
        os.system("lame -V 4 -q %s %s" %(audiofile.retrieveFile(), path+".mp3"))
        ret = path+".mp3"
    node.addFile(FileNode(name=path+".mp3", type="mp3", mimetype="audio/mpeg"))
    return ret
        
# """ make thumbnail (jpeg 128x128) """
def makeThumbNail(node, audiofile):
    import Image,ImageDraw
    path, ext = splitfilename(audiofile.filename)

    if audiofile.tags:
        for k in audiofile.tags:
            if k=="APIC:thumbnail":
                fout = open(path+".thumb", "wb")
                fout.write(audiofile.tags[k].data)
                fout.close()
                
                pic = Image.open(path+".thumb2")
                width = pic.size[0]
                height = pic.size[1]
                
                if width > height:
                    newwidth = 128
                    newheight = height*newwidth/width
                else:
                    newheight = 128
                    newwidth = width*newheight/height
                pic = pic.resize((newwidth, newheight), Image.ANTIALIAS)
                pic.save(path+".thumb", "jpeg")
                pic = pic.resize((newwidth, newheight), Image.ANTIALIAS)
                im = Image.new(pic.mode, (128, 128), (255, 255, 255))
                
                x = (128-newwidth)/2
                y = (128-newheight)/2
                im.paste( pic, (x,y,x+newwidth,y+newheight))
                
                draw = ImageDraw.ImageDraw(im)
                draw.line([(0,0),(127,0),(127,127),(0,127),(0,0)], (128,128,128))
                
                im = im.convert("RGB")
                im.save(path+".thumb", "jpeg")

                node.addFile(FileNode(name=path+".thumb", type="thumb", mimetype=audiofile.tags[k].mime))
                break
            

# """ make presentation format (jpeg 320x320) """    
def makePresentationFormat(node, audiofile):
    import Image,ImageDraw
    path, ext = splitfilename(audiofile.filename)
    
    if audiofile.tags:
        for k in audiofile.tags:
            if k=="APIC:thumbnail":
                fout = open(path+".thumb2", "wb")
                fout.write(audiofile.tags[k].data)
                fout.close()
                
                pic = Image.open(path+".thumb2")
                width = pic.size[0]
                height = pic.size[1]
                
                if width > height:
                    newwidth = 320
                    newheight = height*newwidth/width
                else:
                    newheight = 320
                    newwidth = width*newheight/height
                pic = pic.resize((newwidth, newheight), Image.ANTIALIAS)
                pic.save(path+".thumb2", "jpeg")
                node.addFile(FileNode(name=path+".thumb2", type="presentation", mimetype=audiofile.tags[k].mime))
                break

            
def makeMetaData(node, audiofile):
    global audio_frames
    
    node.set("mp3.version", audiofile.info.version)
    node.set("mp3.layer", audiofile.info.layer)
    node.set("mp3.bitrate", str(int(audiofile.info.bitrate)/1000)+" kBit/s")
    node.set("mp3.sample_rate", str(float(audiofile.info.sample_rate)/1000)+" kHz")

    _s = int(audiofile.info.length % 60)
    _m = audiofile.info.length/60
    _h = int(audiofile.info.length) /3600
    
    node.set("mp3.length", format_date(make_date(0,0,0,_h,_m,_s), '%Y-%m-%dT%H:%M:%S'))
    
    if audiofile.tags:
        for key in audio_frames.keys():
            if key in audiofile.tags.keys():
                node.set("mp3."+audio_frames[key], audiofile.tags[key])

                
""" audio class for internal audio-type """
class Audio(default.Default):
    def getTypeAlias(node):
        return "audio"
        
    def getCategoryName(node):
        return "audio"

        
    # prepare hash table with values for TAL-template
    def _prepareData(node, req):
        access = acl.AccessData(req)     
        mask = node.getFullView(lang(req))

        obj = {}
        if mask:
            obj['metadata'] = mask.getViewHTML([node], VIEW_HIDE_EMPTY, lang(req), mask=mask) # hide empty elements
        else:
            obj['metadata'] = []
        obj['node'] = node  
        obj['path'] = req and req.params.get("path","") or ""
        obj['audiothumb'] = '/thumb2/'+str(node.id)
        if node.has_object():
            obj['canseeoriginal'] = access.hasAccess(node,"data")
            obj['audiolink'] = '/file/'+str(node.id)+'/'+node.getName()
            obj['audiodownload'] = '/download/'+str(node.id)+'/'+node.getName()
        else:
            obj['canseeoriginal']= False
        
        return obj
        
    """ format big view with standard template """
    def show_node_big(node, req, template="", macro=""):
        if template=="":
            styles = getContentStyles("bigview", contenttype=node.getContentType())
            if len(styles)>=1:
                template = styles[0].getTemplate()
        return req.getTAL(template, node._prepareData(req), macro)
    
    def isContainer(node):
        return 0

    def getLabel(node):
        return node.name
        
    def has_object(node):
        for f in node.getFiles():
            if f.type=="audio":
                return True
        return False
        
    def getSysFiles(node):
        return ["audio","thumb","presentation","mp3"]

    """ postprocess method for object type 'audio'. called after object creation """
    def event_files_changed(node):
        print "Postprocessing node",node.id
        
        original = None
        audiothumb = None
        thumb = None
        thumb2 = None
        
        for f in node.getFiles():
            if f.type=="audio":
                original = f
            if f.type=="mp3":
                audiothumb = f
            if f.type.startswith("present"):
                thumb2 = f
            if f.type=="thumb":
                thumb = f

        if original:

            if audiothumb:
                node.removeFile(audiothumb)
            if thumb: # delete old thumb
                node.removeFile(thumb)
            if thumb2: # delete old thumb2
                node.removeFile(thumb2)

            athumb = makeAudioThumb(node, original)
            if athumb:
                _original = AudioFile(athumb)
            else:
                _original = AudioFile(original.retrieveFile())
            makePresentationFormat(node, _original)
            makeThumbNail(node, _original)
            makeMetaData(node, _original)
            
    """ list with technical attributes for type image """
    def getTechnAttributes(node):
        return {}
    
    def getDuration(node):
        return format_date(parse_date(node.get("mp3.length")), '%H:%M:%S')
    
    def getEditMenuTabs(node):
        return "menulayout(view);menumetadata(metadata;files;admin;lza);menuclasses(classes);menusecurity(acls)"

    def getDefaultEditTab(node):
        return "view"
        
        
    def processMediaFile(node, dest):
        for file in node.getFiles():
            if file.getType()=="audio":
                filename = file.retrieveFile()
                path, ext = splitfilename(filename)
                if os.sep=='/':
                    ret = os.system("cp %s %s" %(filename, dest))
                else:
                    cmd = "copy %s %s%s.%s" %(filename, dest, node.id, ext)
                    ret = os.system(cmd.replace('/','\\'))
        return 1
        
        
        
audio_frames = {"AENC": "audio_encryption",\
"APIC": "attached_picture",\
"COMM": "comments",\
"COMR": "commercial_frame",\
"ENCR": "encryption_method_registration",\
"EQUA": "equalization",\
"ETCO": "event_timing_codes",\
"GEOB": "general_encapsulated_object",\
"GRID": "group_identification_registration",\
"IPLS": "involved_people_list",\
"LINK": "linked_information",\
"MCDI": "music_cd_dentifier",\
"MLLT": "mpeg_location_lookup_table",\
"OWNE": "ownership_frame",\
"PRIV": "private_frame",\
"PCNT": "play_counter",\
"POPM": "popularimeter",\
"POSS": "position_synchronisation_frame",\
"RBUF": "recommended_buffer_size",\
"RVAD": "relative_volume_adjustment",\
"RVRB": "reverb",\
"SYLT": "synchronized_lyric_text",\
"SYTC": "synchronized_tempo_codes",\
"TALB": "album_title",\
"TBPM": "bpm",\
"COM ": "composer",\
"TCON": "genre",\
"TCOP": "copyright_message",\
"TDAT": "date",\
"TDLY": "playlist_delay",\
"TENC": "encoded_by",\
"TEXT": "text_writer",\
"TFLT": "file_type",\
"TIME": "time",\
"TIT1": "content_group_description",\
"TIT2": "title",\
"TIT3": "subtitle",\
"TKEY": "initial_key",\
"TLAN": "language",\
"TLEN": "length",\
"TMED": "media_type",\
"TOAL": "original_album_title",\
"TOFN": "original_filename",\
"TOLY": "original_lyricist_writer",\
"TOPE": "original_artist",\
"TORY": "original_release_year",\
"TOWN": "file_owner",\
"TPE1": "performer",\
"TPE2": "band",\
"TPE3": "conductor",\
"TPE4": "interpreted_by",\
"TPOS": "part_of_set",\
"TPUB": "publisher",\
"TRCK": "track",\
"TRDA": "recording_dates",\
"TRSN": "internet_station_name",\
"TRSO": "internet_station_owner",\
"TSIZ": "size",\
"TSRC": "isrc",\
"TSSE": "encoding_settings",\
"TYER": "year",\
"TXXX": "user_text",\
"UFID": "file_identifier",\
"USER": "terms_of_use",\
"USLT": "unsychronized_text_transcription",\
"WCOM": "commercial_information",\
"WCOP": "copyright_information",\
"WOAF": "audio_webpage",\
"WOAR": "artist_webpage",\
"WOAS": "source_webpage",\
"WORS": "radio_homepage",\
"WPAY": "payment",\
"WPUB": "publishers_webpage",\
"WXXX": "user_defined_url"}
