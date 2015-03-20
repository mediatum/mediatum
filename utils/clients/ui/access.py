# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details
    
    Python access layer for the mediaTUM web UI
"""


from nap.url import Url
from utils.clients.sessionurl import SessionUrl


class MediatumAccessMixin(object):

    """Some helper methods for common mediaTUM access.
    This covers all parts of mediaTUM, could be split in multiple mixins later
    """

    def login(self, user="Administrator", password="xadmin1", **kwargs):
        res = self.post("/login", data=dict(user=user, password=password, LoginSubmit=True), **kwargs)
        return res

    def get_node(self, node_id, **kwargs):
        return self.get("/node", params=dict(id=node_id), **kwargs)

    def unfold(self, node_id, **kwargs):
        return self.get("/", params=dict(id=node_id, cfold=node_id, dir=node_id), **kwargs)

    def search(self, query, act_node, start_search, searchmode="simple", **kwargs):
        return self.post("/node",
                         data=dict(query=query, act_node=act_node, start_search=start_search, searchmode=searchmode),
                         **kwargs)

    def change_language(self, lang, **kwargs):
        return self.get("/", params=dict(change_language=lang))


class MediatumUrlMixin(object):

    """ Sets a default URL and after_request handler for mediaTUM access
    """
    # override this if you like to test another instance
    # could be overridden by a --base-url option if used with py.test, for example
    BASE_URL = "http://localhost:8081"

    def after_request(self, response):
        """Raises an exception if the HTTP status code indicates a failure"""
        response.raise_for_status()
        return response


class MediatumWebUI(MediatumAccessMixin, MediatumUrlMixin, Url):

    """Access the mediaTUM web UI via this class. Stateless, doesn't save cookies!
    """

    def __init__(self, url=None, **default_kwargs):
        super(MediatumWebUI, self).__init__(url or self.BASE_URL, **default_kwargs)


class MediatumWebUISession(MediatumAccessMixin, MediatumUrlMixin, SessionUrl):

    """Access the mediaTUM web UI via this class. This client is stateful and remembers cookies.
    """

    def __init__(self, url=None, **default_kwargs):
        super(MediatumWebUISession, self).__init__(url or self.BASE_URL, **default_kwargs)
        self.new_session()