# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
import tempfile
import nap.url
from sh import sdiff
import codecs
from lxml import etree
import json
import logging


logg = logging.getLogger(__name__)

candidate = nap.url.Url("http://localhost:8082")
primary = nap.url.Url("http://localhost:8083")
secondary = nap.url.Url("http://localhost:8083")
#primary = nap.url.Url("http://mediatum.ub.tum.de")
#secondary = nap.url.Url("http://mediatum.ub.tum.de")


def diff(url):
    res_candidate = candidate.get(url)

    baselines, mimetype = diffbase(url)

    base = "\n".join(baselines)

    if mimetype.endswith("xml"):
        try:
            xmlroot = etree.fromstring(base)
            base = etree.tostring(xmlroot, xml_declaration=True, pretty_print=True)
        except:
            logg.info("mimetype xml, but could not be parsed as xml")
            pass
    else:
        try:
            js = json.loads(base)
            base = json.dumps(js)
        except:
            pass

    with codecs.open("/tmp/merged", "w", encoding="utf8") as wf:
        wf.write(base)


    filtered = []

    for b, c in zip(baselines, res_candidate.text.replace("\r\n", "<RN_NEWLINE>").splitlines()):
        if b:
            filtered.append(c.replace("<RN_NEWLINE>", "\r\n"))
        else:
            filtered.append("")

    with codecs.open("/tmp/candidate", "w", encoding="utf8") as wf:
        wf.write("\n".join(filtered))


def diffbase(url):
    res_primary = primary.get(url)
    res_secondary = secondary.get(url)

    primary_f = tempfile.NamedTemporaryFile("w")
    secondary_f = tempfile.NamedTemporaryFile("w")


    primary_f.write(res_primary.content.replace("\r\n", "<RN_NEWLINE>"))
    secondary_f.write(res_secondary.content.replace("\r\n", "<RN_NEWLINE>"))

    primary_f.flush()
    secondary_f.flush()

    diffed = sdiff("-d", "-Z", "-b", "-l", "-w", "300000", primary_f.name, secondary_f.name, _ok_code=[0, 1])

    filtered = []
    for line in diffed.splitlines():
        if line.endswith("("):
            filtered.append(line[:-1].replace("<RN_NEWLINE>", "\r\n").rstrip("\t "))
        else:
            filtered.append("")

    return filtered, res_primary.headers["content-type"]


diff("services/export/node/1239873/allchildren?lang=de&attrspec=all&format=xml&sortfield=author-contrib")