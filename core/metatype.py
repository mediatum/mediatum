"""
 mediatum - a multimedia content repository

 Copyright (C) 2007 Arne Seifert <seiferta@in.tum.de>
 Copyright (C) 2007 Matthias Kramm <kramm@in.tum.de>
 Copyright (C) 2013 Iryna Feuerstein <feuersti@in.tum.de>

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

from warnings import warn


class Context(object):

    def __init__(self, field, value="", width=400, name="", lock=0, language=None, collection=None, container=None, user=None, ip=""):
        if collection is not None:
            warn("collections argument is deprecated, use container", DeprecationWarning)
            if container is not None:
                raise ValueError("container and collection cannot be used together")
            container = collection

        self.field = field
        self.value = value
        self.width = width
        self.name = name
        self.language = language
        self.collection = container
        self.container = container
        self.ip = ip
        self.user = user
        self.lock = lock


class Metatype(object):

    joiner = '\n'

    def getEditorHTML(self, field, value="", width=400, lock=0, language=None, required=None):
        return ""

    def getSearchHTML(self, context):
        None

    def getFormattedValue(self, metafield, maskitem, mask, node, language, html):
        None

    def format_request_value_for_db(self, field, params, item, language=None):
        """Prepare value for the database from update request params.
        :param field:   associated field
        :param params: dict which contains POST form values
        :param item: field name prepended with language specifier. Is the same as field name for non-multilingual fields.
        """
        # just fetch the unmodified alue from the params dict
        return params.get(item)

    def getMaskEditorHTML(self, field, metadatatype=None, language=None):
        return ""

    @classmethod
    def isContainer(cls):
        return False

    def isFieldType(self):
        return True

    def getName(self):
        return ""

    def getInformation(self):
        return {"moduleversion": "1.0"}

    ''' events '''

    def event_metafield_changed(self, node, field):
        None

    def get_input_pattern(self, field):
        return ''

    def get_input_title(self, field):
        return ''

    def get_input_placeholder(self, field):
        return ''

    def is_required(self, required):
        """
        It's necessary to return different types in order for the template to render properly.
        Since required='' or even required='False' is still interpreted as a required field,
        it needs to be completely removed from the template where applicable. TAL attributes
        are removed if they evaluate to None.
        @param required: 0 or 1
        @return: str True or None object
        """
        if required:
            return 'True'
        else:
            return None

charmap = [
    ['&nbsp;', '160', 'no-break space'],
    ['&amp;', '38', 'ampersand'],
    ['&quot;', '34', 'quotation mark'],
    # finance
    ['&cent;', '162', 'cent sign'],
    ['&euro;', '8364', 'euro sign'],
    ['&pound;', '163', 'pound sign'],
    ['&yen;', '165', 'yen sign'],
    # signs
    ['&copy;', '169', 'copyright sign'],
    ['&reg;', '174', 'registered sign'],
    ['&trade;', '8482', 'trade mark sign'],
    ['&permil;', '8240', 'per mille sign'],
    ['&micro;', '181', 'micro sign'],
    ['&middot;', '183', 'middle dot'],
    ['&bull;', '8226', 'bullet'],
    ['&hellip;', '8230', 'three dot leader'],
    ['&prime;', '8242', 'minutes / feet'],
    ['&Prime;', '8243', 'seconds / inches'],
    ['&sect;', '167', 'section sign'],
    ['&para;', '182', 'paragraph sign'],
    ['&szlig;', '223', 'sharp s / ess-zed'],
    # quotations
    ['&lsaquo;', '8249', 'single left-pointing angle quotation mark'],
    ['&rsaquo;', '8250', 'single right-pointing angle quotation mark'],
    ['&laquo;', '171', 'left pointing guillemet'],
    ['&raquo;', '187', 'right pointing guillemet'],
    ['&lsquo;', '8216', 'left single quotation mark'],
    ['&rsquo;', '8217', 'right single quotation mark'],
    ['&ldquo;', '8220', 'left double quotation mark'],
    ['&rdquo;', '8221', 'right double quotation mark'],
    ['&sbquo;', '8218', 'single low-9 quotation mark'],
    ['&bdquo;', '8222', 'double low-9 quotation mark'],
    ['&lt;', '60', 'less-than sign'],
    ['&gt;', '62', 'greater-than sign'],
    ['&le;', '8804', 'less-than or equal to'],
    ['&ge;', '8805', 'greater-than or equal to'],
    ['&ndash;', '8211', 'en dash'],
    ['&mdash;', '8212', 'em dash'],
    ['&macr;', '175', 'macron'],
    ['&oline;', '8254', 'overline'],
    ['&curren;', '164', 'currency sign'],
    ['&brvbar;', '166', 'broken bar'],
    ['&uml;', '168', 'diaeresis'],
    ['&iexcl;', '161', 'inverted exclamation mark'],
    ['&iquest;', '191', 'turned question mark'],
    ['&circ;', '710', 'circumflex accent'],
    ['&tilde;', '732', 'small tilde'],
    ['&deg;', '176', 'degree sign'],
    ['&minus;', '8722', 'minus sign'],
    ['&plusmn;', '177', 'plus-minus sign'],
    ['&divide;', '247', 'division sign'],
    ['&frasl;', '8260', 'fraction slash'],
    ['&times;', '215', 'multiplication sign'],
    ['&sup1;', '185', 'superscript one'],
    ['&sup2;', '178', 'superscript two'],
    ['&sup3;', '179', 'superscript three'],
    ['&frac14;', '188', 'fraction one quarter'],
    ['&frac12;', '189', 'fraction one half'],
    ['&frac34;', '190', 'fraction three quarters'],
    # math / logical
    ['&fnof;', '402', 'function / florin'],
    ['&int;', '8747', 'integral'],
    ['&sum;', '8721', 'n-ary sumation'],
    ['&infin;', '8734', 'infinity'],
    ['&radic;', '8730', 'square root'],
    ['&sim;', '8764', 'similar to'],
    ['&cong;', '8773', 'approximately equal to'],
    ['&asymp;', '8776', 'almost equal to'],
    ['&ne;', '8800', 'not equal to'],
    ['&equiv;', '8801', 'identical to'],
    ['&isin;', '8712', 'element of'],
    ['&notin;', '8713', 'not an element of'],
    ['&ni;', '8715', 'contains as member'],
    ['&prod;', '8719', 'n-ary product'],
    ['&and;', '8743', 'logical and'],
    ['&or;', '8744', 'logical or'],
    ['&not;', '172', 'not sign'],
    ['&cap;', '8745', 'intersection'],
    ['&cup;', '8746', 'union'],
    ['&part;', '8706', 'partial differential'],
    ['&forall;', '8704', 'for all'],
    ['&exist;', '8707', 'there exists'],
    ['&empty;', '8709', 'diameter'],
    ['&nabla;', '8711', 'backward difference'],
    ['&lowast;', '8727', 'asterisk operator'],
    ['&prop;', '8733', 'proportional to'],
    ['&ang;', '8736', 'angle'],
    # undefined
    ['&acute;', '180', 'acute accent'],
    ['&cedil;', '184', 'cedilla'],
    ['&ordf;', '170', 'feminine ordinal indicator'],
    ['&ordm;', '186', 'masculine ordinal indicator'],
    ['&dagger;', '8224', 'dagger'],
    ['&Dagger;', '8225', 'double dagger'],
    # alphabetical special chars
    ['&Agrave;', '192', 'A - grave'],
    ['&Aacute;', '193', 'A - acute'],
    ['&Acirc;', '194', 'A - circumflex'],
    ['&Atilde;', '195', 'A - tilde'],
    ['&Auml;', '196', 'A - diaeresis'],
    ['&Aring;', '197', 'A - ring above'],
    ['&AElig;', '198', 'ligature AE'],
    ['&Ccedil;', '199', 'C - cedilla'],
    ['&Egrave;', '200', 'E - grave'],
    ['&Eacute;', '201', 'E - acute'],
    ['&Ecirc;', '202', 'E - circumflex'],
    ['&Euml;', '203', 'E - diaeresis'],
    ['&Igrave;', '204', 'I - grave'],
    ['&Iacute;', '205', 'I - acute'],
    ['&Icirc;', '206', 'I - circumflex'],
    ['&Iuml;', '207', 'I - diaeresis'],
    ['&ETH;', '208', 'ETH'],
    ['&Ntilde;', '209', 'N - tilde'],
    ['&Ograve;', '210', 'O - grave'],
    ['&Oacute;', '211', 'O - acute'],
    ['&Ocirc;', '212', 'O - circumflex'],
    ['&Otilde;', '213', 'O - tilde'],
    ['&Ouml;', '214', 'O - diaeresis'],
    ['&Oslash;', '216', 'O - slash'],
    ['&OElig;', '338', 'ligature OE'],
    ['&Scaron;', '352', 'S - caron'],
    ['&Ugrave;', '217', 'U - grave'],
    ['&Uacute;', '218', 'U - acute'],
    ['&Ucirc;', '219', 'U - circumflex'],
    ['&Uuml;', '220', 'U - diaeresis'],
    ['&Yacute;', '221', 'Y - acute'],
    ['&Yuml;', '376', 'Y - diaeresis'],
    ['&THORN;', '222', 'THORN'],
    ['&agrave;', '224', 'a - grave'],
    ['&aacute;', '225', 'a - acute'],
    ['&acirc;', '226', 'a - circumflex'],
    ['&atilde;', '227', 'a - tilde'],
    ['&auml;', '228', 'a - diaeresis'],
    ['&aring;', '229', 'a - ring above'],
    ['&aelig;', '230', 'ligature ae'],
    ['&ccedil;', '231', 'c - cedilla'],
    ['&egrave;', '232', 'e - grave'],
    ['&eacute;', '233', 'e - acute'],
    ['&ecirc;', '234', 'e - circumflex'],
    ['&euml;', '235', 'e - diaeresis'],
    ['&igrave;', '236', 'i - grave'],
    ['&iacute;', '237', 'i - acute'],
    ['&icirc;', '238', 'i - circumflex'],
    ['&iuml;', '239', 'i - diaeresis'],
    ['&eth;', '240', 'eth'],
    ['&ntilde;', '241', 'n - tilde'],
    ['&ograve;', '242', 'o - grave'],
    ['&oacute;', '243', 'o - acute'],
    ['&ocirc;', '244', 'o - circumflex'],
    ['&otilde;', '245', 'o - tilde'],
    ['&ouml;', '246', 'o - diaeresis'],
    ['&oslash;', '248', 'o slash'],
    ['&oelig;', '339', 'ligature oe'],
    ['&scaron;', '353', 's - caron'],
    ['&ugrave;', '249', 'u - grave'],
    ['&uacute;', '250', 'u - acute'],
    ['&ucirc;', '251', 'u - circumflex'],
    ['&uuml;', '252', 'u - diaeresis'],
    ['&yacute;', '253', 'y - acute'],
    ['&thorn;', '254', 'thorn'],
    ['&yuml;', '255', 'y - diaeresis'],
    ['&Alpha;', '913', 'Alpha'],
    ['&Beta;', '914', 'Beta'],
    ['&Gamma;', '915', 'Gamma'],
    ['&Delta;', '916', 'Delta'],
    ['&Epsilon;', '917', 'Epsilon'],
    ['&Zeta;', '918', 'Zeta'],
    ['&Eta;', '919', 'Eta'],
    ['&Theta;', '920', 'Theta'],
    ['&Iota;', '921', 'Iota'],
    ['&Kappa;', '922', 'Kappa'],
    ['&Lambda;', '923', 'Lambda'],
    ['&Mu;', '924', 'Mu'],
    ['&Nu;', '925', 'Nu'],
    ['&Xi;', '926', 'Xi'],
    ['&Omicron;', '927', 'Omicron'],
    ['&Pi;', '928', 'Pi'],
    ['&Rho;', '929', 'Rho'],
    ['&Sigma;', '931', 'Sigma'],
    ['&Tau;', '932', 'Tau'],
    ['&Upsilon;', '933', 'Upsilon'],
    ['&Phi;', '934', 'Phi'],
    ['&Chi;', '935', 'Chi'],
    ['&Psi;', '936', 'Psi'],
    ['&Omega;', '937', 'Omega'],
    ['&alpha;', '945', 'alpha'],
    ['&beta;', '946', 'beta'],
    ['&gamma;', '947', 'gamma'],
    ['&delta;', '948', 'delta'],
    ['&epsilon;', '949', 'epsilon'],
    ['&zeta;', '950', 'zeta'],
    ['&eta;', '951', 'eta'],
    ['&theta;', '952', 'theta'],
    ['&iota;', '953', 'iota'],
    ['&kappa;', '954', 'kappa'],
    ['&lambda;', '955', 'lambda'],
    ['&mu;', '956', 'mu'],
    ['&nu;', '957', 'nu'],
    ['&xi;', '958', 'xi'],
    ['&omicron;', '959', 'omicron'],
    ['&pi;', '960', 'pi'],
    ['&rho;', '961', 'rho'],
    ['&sigmaf;', '962', 'final sigma'],
    ['&sigma;', '963', 'sigma'],
    ['&tau;', '964', 'tau'],
    ['&upsilon;', '965', 'upsilon'],
    ['&phi;', '966', 'phi'],
    ['&chi;', '967', 'chi'],
    ['&psi;', '968', 'psi'],
    ['&omega;', '969', 'omega'],
    # symbols
    ['&alefsym;', '8501', 'alef symbol'],
    ['&piv;', '982', 'pi symbol'],
    ['&real;', '8476', 'real part symbol'],
    ['&thetasym;', '977', 'theta symbol'],
    ['&upsih;', '978', 'upsilon - hook symbol'],
    ['&weierp;', '8472', 'Weierstrass p'],
    ['&image;', '8465', 'imaginary part'],
    # arrows
    ['&larr;', '8592', 'leftwards arrow'],
    ['&uarr;', '8593', 'upwards arrow'],
    ['&rarr;', '8594', 'rightwards arrow'],
    ['&darr;', '8595', 'downwards arrow'],
    ['&harr;', '8596', 'left right arrow'],
    ['&crarr;', '8629', 'carriage return'],
    ['&lArr;', '8656', 'leftwards double arrow'],
    ['&uArr;', '8657', 'upwards double arrow'],
    ['&rArr;', '8658', 'rightwards double arrow'],
    ['&dArr;', '8659', 'downwards double arrow'],
    ['&hArr;', '8660', 'left right double arrow'],
    ['&there4;', '8756', 'therefore'],
    ['&sub;', '8834', 'subset of'],
    ['&sup;', '8835', 'superset of'],
    ['&nsub;', '8836', 'not a subset of'],
    ['&sube;', '8838', 'subset of or equal to'],
    ['&supe;', '8839', 'superset of or equal to'],
    ['&oplus;', '8853', 'circled plus'],
    ['&otimes;', '8855', 'circled times'],
    ['&perp;', '8869', 'perpendicular'],
    ['&sdot;', '8901', 'dot operator'],
    ['&lceil;', '8968', 'left ceiling'],
    ['&rceil;', '8969', 'right ceiling'],
    ['&lfloor;', '8970', 'left floor'],
    ['&rfloor;', '8971', 'right floor'],
    ['&lang;', '9001', 'left-pointing angle bracket'],
    ['&rang;', '9002', 'right-pointing angle bracket'],
    ['&loz;', '9674', 'lozenge'],
    ['&spades;', '9824', 'black spade suit'],
    ['&clubs;', '9827', 'black club suit'],
    ['&hearts;', '9829', 'black heart suit'],
    ['&diams;', '9830', 'black diamond suit'],
    ['&ensp;', '8194', 'en space'],
    ['&emsp;', '8195', 'em space'],
    ['&thinsp;', '8201', 'thin space'],
    ['&zwnj;', '8204', 'zero width non-joiner'],
    ['&zwj;', '8205', 'zero width joiner'],
    ['&lrm;', '8206', 'left-to-right mark'],
    ['&rlm;', '8207', 'right-to-left mark'],
    ['&shy;', '173', 'soft hyphen']
]
