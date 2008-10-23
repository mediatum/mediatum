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
import core.users
import core.config as config

SocketError = "socketerror"

def sendmail(fromemail, email, subject, text):
    testing = config.get("host.type") == "testing"
    fromaddr = fromemail

    try:
        text = unicode(text, "utf-8").encode("latin1")
    except:
        print formatException()


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

    msg = """From: %s\nTo: %s\nSubject: %s\n\n%s""" % (fromaddr, toaddrs_string, subject, text)
    print "Sending mail from %s to %s" % (fromaddr, toaddrs)
    if not testing:
        try:
            server = smtplib.SMTP(config.get("server.mail"))
            server.set_debuglevel(1)
            server.sendmail(fromaddr, toaddrs, msg)
            server.quit()
        except smtplib.socket.error:
            raise SocketError
    else:
        print msg
