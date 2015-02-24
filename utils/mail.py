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
import smtplib

import mimetypes

from email import encoders
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import codecs
import os
import logging
import core.config as config
from .utils import formatException

SocketError = "socketerror"
logg = logging.getLogger(__name__)


def sendmail(fromemail, email, subject, text, attachments_paths_and_filenames=[]):
    testing = config.get("host.type") == "testing"
    fromaddr = fromemail

    if ";" in email:
        toaddrs = []
        toaddrs_string = ""
        for x in email.split(';'):
            x = x.strip()
            if x:
                toaddrs += [x]
                if toaddrs_string:
                    toaddrs_string += ", "
                toaddrs_string += x
    else:
        toaddrs = email
        toaddrs_string = email

    logg.info("Sending mail from %s to %s", fromaddr, toaddrs)
    if not testing:
        if not attachments_paths_and_filenames:
            try:
                text = unicode(text, "utf-8").encode("latin1")
            except:
                logg.exception("exception in sendmail, ignoring")
                
            msg = """From: %s\nTo: %s\nSubject: %s\n\n%s""" % (fromaddr, toaddrs_string, subject, text)
            try:
                server = smtplib.SMTP(config.get("server.mail"))
                server.set_debuglevel(1)
                server.sendmail(fromaddr, toaddrs, msg)
                server.quit()
            except smtplib.socket.error:
                raise SocketError
        else:
            try:
                mime_multipart = MIMEMultipart()
                mime_multipart['Subject'] = subject
                mime_multipart['To'] = toaddrs_string
                mime_multipart['From'] = fromaddr

                text = text.replace("\r", "\r\n")

                msg = MIMEText(text, _subtype="plain", _charset="utf-8")

                mime_multipart.attach(msg)
                # from exapmle in python docu
                for path, filename in attachments_paths_and_filenames:
                    if not os.path.isfile(path):
                        logg.error("error sending mail to '%s' ('%s'): attachment: no such file: '%s', skipping file", 
                                   toaddrs_string, subject, path)
                        continue
                    ctype, encoding = mimetypes.guess_type(path)
                    if ctype is None or encoding is not None:
                        ctype = 'application/octet-stream'
                    maintype, subtype = ctype.split('/', 1)
                    if maintype == 'text':
                        # tested with ansi and utf-8
                        with codecs.open(path, 'r', encoding='utf8') as fp:
                            msg = MIMEText(fp.read(), _subtype=subtype)
                    else:
                        with open(path, 'rb', encoding='utf8') as fp:
                            if maintype == 'image':
                                msg = MIMEImage(fp.read(), _subtype=subtype)
                            elif maintype == 'audio':
                                msg = MIMEAudio(fp.read(), _subtype=subtype)
                            else:
                                msg = MIMEBase(maintype, subtype)
                                msg.set_payload(fp.read())
                                encoders.encode_base64(msg)
                    msg.add_header('Content-Disposition', 'attachment', filename=filename)
                    mime_multipart.attach(msg)

                composed = mime_multipart.as_string()

                server = smtplib.SMTP(config.get("server.mail"))
                server.sendmail(fromaddr, toaddrs, composed)
                server.quit()
                logg.info("sent email to '%s' ('%s'): attachments: '%s'",toaddrs_string, subject, attachments_paths_and_filenames)
            except Exception:
                logg.exception("exception sending mail!")
                raise
