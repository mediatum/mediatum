# -*- coding: utf-8 -*-

# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import division
from __future__ import print_function

import logging
import hashlib
import utils.utils as _utils_utils
from core import db
from core.database.postgres.user import OAuthUserCredentials

q = db.query

logg = logging.getLogger(__name__)

logg.info("imported core.oauth")


def verify_request_signature(req_path, params):
    # we generate the signature from the shared secret, the request path and all sorted parameters
    # as described in the upload api documentation
    _p = params.copy()

    fmsg = "verify_request_signature going to return False: "
    if 'user' not in _p or 'sign' not in _p:
        logg.info("%s'user' or 'sign' parameter missing in request", fmsg)
        return False

    oauth_user = _p.get('user')
    oauth_user_credentials_count = q(OAuthUserCredentials).filter(OAuthUserCredentials.oauth_user == oauth_user).count()
    if oauth_user_credentials_count < 1:
        logg.info("%sno oauth user credentials known for oauth_user %r", fmsg, oauth_user)
        return False
    if oauth_user_credentials_count > 1:
        logg.info("%smultiple oauth user credentials stored for oauth_user %r", fmsg, oauth_user)
        return False
    oauth_user_credentials = q(OAuthUserCredentials).filter(OAuthUserCredentials.oauth_user == oauth_user).one()
    workingString = oauth_user_credentials.oauth_key

    #try:
    #    workingString = ""
    #    for n in [h for h in tree.getRoot('home').getChildren() if h.get('system.oauthuser') == params.get('user')]:
    #        workingString = n.get('system.oauthkey')
    #        break
    #except:
    #    return False

    workingString += req_path

    # remove signature form parameters before we calculate the test signature
    signature = _p['sign']
    del _p['sign']

    keylist = sorted(_p.keys())

    isFirst = True

    for oneKey in keylist:
        oneValue = _p[oneKey]
        if not isFirst:
            workingString += '&'
        else:
            isFirst = False
        workingString += '{}={}'.format(oneKey,
                                        oneValue)
    testSignature = hashlib.md5(workingString).hexdigest()
    return (testSignature == signature)


def get_oauth_key_for_user(user):
        login_name = user.login_name
        oauth_user_credentials_count = q(OAuthUserCredentials).filter(OAuthUserCredentials.oauth_user == login_name).filter(OAuthUserCredentials.user_id == user.id).count()
        if oauth_user_credentials_count == 0:
            oauthkey = ''
        elif oauth_user_credentials_count == 1:
            # retrieve that key
            oauth_user_credentials = q(OAuthUserCredentials).filter(OAuthUserCredentials.oauth_user == login_name).filter(OAuthUserCredentials.user_id == user.id).one()
            oauthkey = oauth_user_credentials.oauth_key
        else:
            oauthkey = ''
            pass  #raise exception?  should not happen: unique constraint on column oauth_user
        return oauthkey


def generate_new_oauth_key_for_user(user):
    s = db.session

    generated_key = _utils_utils.gen_secure_token() # generate key

    user_login_name = user.login_name

    oauth_user_credentials_count = q(OAuthUserCredentials).filter(OAuthUserCredentials.oauth_user == user_login_name).filter(OAuthUserCredentials.user_id == user.id).count()
    if oauth_user_credentials_count == 0:
        oauth_user_credentials = OAuthUserCredentials(oauth_user=user_login_name, oauth_key=generated_key, user_id=user.id)
        s.add(oauth_user_credentials)
        s.commit()
    elif oauth_user_credentials_count == 1:
        oauth_user_credentials = s.query(OAuthUserCredentials).filter(OAuthUserCredentials.oauth_user == unicode(user_login_name)).filter(OAuthUserCredentials.user_id == user.id)
        oauth_user_credentials.update({'oauth_key': generated_key})
        s.commit()
    else:
        pass  #raise exception? should not happen: unique constraint on column oauth_user

    return generated_key
