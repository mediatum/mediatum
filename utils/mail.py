# -*- coding: utf-8 -*-

# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import collections as _collections
import smtplib

import mimetypes

from email import encoders
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import email.quoprimime as _email_quoprimime
import email.utils as _email_utils

import codecs
import os
import logging
import core.config as config
from .utils import formatException

SocketError = "socketerror"
logg = logging.getLogger(__name__)


class EmailAddress(_collections.namedtuple("EmailAddress", "address name")):
    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
         assert "@" in self.address
         assert "<" not in self.address
         assert ">" not in self.address
         if self.name is not None:
             assert "<" not in self.name
             assert ">" not in self.name
             assert '"' not in self.name
             return u'"{name}" <{address}>'.format(**self._asdict())
         return unicode(self.address)

    @property
    def rfc2045(self):
        return _email_utils.formataddr((
            None if self.name is None else _email_quoprimime.header_encode(self.name),
            self.address,
           ))


def sendmail(sender, recipients, subject, text, envelope_sender_address=None, attachments={}, reply_to=None):
    assert envelope_sender_address is None or "@" in envelope_sender_address
    host = config.get("smtp-server.host")
    if not host:
        raise RuntimeError("No email server specified, not sending email")

    encryption = config.get("smtp-server.encryption")
    if encryption == "tls":
        server = smtplib.SMTP_SSL(host, port=config.get("smtp-server.port", 465))
    else:
        server = smtplib.SMTP(host, port=config.get("smtp-server.port", 587))
    if encryption == "starttls":
        server.starttls()
    username = config.get('smtp-server.username')
    if username:
        with open(config.get("smtp-server.password-file"), "rb") as f:
            server.login(username, f.read())

    logg.debug(
        "About to send Email from %s with %s byte(s) text, %s attachment(s) to %s recipient(s): '%s'",
        sender.address,
        len(text),
        len(attachments),
        len(recipients),
        subject,
    )
    mime_multipart = MIMEMultipart()
    mime_multipart['Subject'] = subject
    mime_multipart['To'] = u", ".join(r.rfc2045 for r in recipients)
    mime_multipart['From'] = sender.rfc2045
    if reply_to is not None:
        mime_multipart["Reply-To"] = reply_to.rfc2045
    text = text.replace("\r", "\r\n")
    msg = MIMEText(text, _subtype="plain", _charset="utf-8")
    mime_multipart.attach(msg)
    # from exapmle in python docu
    for filename, path in attachments.iteritems():
        if not os.path.isfile(path):
            raise RuntimeError("missing attachment file '{}' for mail '{}' to '{}'".format(
                    path, subject, ", ".join(r.address for r in recipients),
                ))
        ctype, encoding = mimetypes.guess_type(path)
        if ctype is None or encoding is not None:
            ctype = 'application/octet-stream'
        maintype, subtype = ctype.split('/', 1)
        if maintype == 'text':
            # tested with ansi and utf-8
            with codecs.open(path, 'r', encoding='utf8') as fp:
                msg = MIMEText(fp.read(), _subtype=subtype, _charset="utf-8")
        else:
            with open(path, 'rb') as fp:
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

    try:
        senderrs = server.sendmail(
                envelope_sender_address or sender.address,
                tuple(r.address for r in recipients),
                composed,
            )
        if senderrs:
            raise RuntimeError("failed to send email to: {}".format(", ".join(senderrs)))
    finally:
        server.quit()
