# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details

Python access layer for the mediaTUM export web service

"""
from __future__ import division
from __future__ import print_function

from urlparse import urljoin
from nap.url import Url

from utils.clients.sessionurl import SessionUrl
from utils.clients.api.objects import APINode, APIShortlist, NodeAPIResult


class CachedHTTPException(Exception):

    def __init__(self, msg, status):
        self.status = status
        full_msg = "Error was: {} {}. " \
            "This is a cached request which returned an error. To evaluate the request again, set acceptcached=0.".format(status, msg)
        super(CachedHTTPException, self).__init__(full_msg)


class MediatumAPIAccessMixin(object):

    """Some generic helper methods for mediaTUM access via the export API.
    """
    _default_additional_params = {}

    def _raise_for_cached_failure(self, data):
        if data["status"] == "fail":
            raise CachedHTTPException(data["errormessage"], int(data["html_response_code"]))

    def _node(self, node_id, request, start=None, limit=None, type=None, sortfield=None, mask=None,
              attrspec=None, attrlist=None, add_shortlist=None, i0=None, i1=None, q=None, additional_params=None, request_kwargs=None):

        params = self._default_additional_params.copy()
        params.update({
            "format": "json",
            "start": start,
            "limit": limit,
            "type": type,
            "sortfield": sortfield,
            "mask": mask,
            "attrspec": attrspec,
            "attrlist": attrlist if attrlist is None or isinstance(attrlist, (str, unicode)) else ",".join(list),
            "add_shortlist": add_shortlist,
            "i0": i0,
            "i1": i1,
            "q": q
        })
        if additional_params:
            params.update(additional_params)
        return self.get("export/node/{}{}".format(node_id, request), params=params, **(request_kwargs or {}))

    def get_node(self, node_id, attrspec=None, attrlist=None, additional_params=None, request_kwargs=None):
        """Fetches a single Node representation
        :param additional_params: query params which will be merged with params created from the method args.
            Params in `additional_params` overwrite other params!
        :param request_kwargs: theses args will be passed to the requests library
        :rtype: Node
        """
        data = self._node(node_id, "", attrspec=attrspec, attrlist=attrlist,
                          additional_params=additional_params, request_kwargs=request_kwargs).json()
        self._raise_for_cached_failure(data)
        return APINode.from_dict(data["nodelist"][0][0])

    def get_nodemask(self, node_id, mask="default", additional_params=None, request_kwargs=None):
        """Fetches rendered content for a given mask.
        :param mask: Name of the mask to render; uses the default export mask if omitted
        :returns: Rendered mask text
        :rtype: unicode
        """
        data = self._node(node_id, "", mask=mask, attrspec="none",
                          additional_params=additional_params, request_kwargs=request_kwargs).json()
        self._raise_for_cached_failure(data)
        return data["nodelist"][0][0]["defaultexport"]

    def children(self, node_id, recursive=False, start=None, limit=None, type=None, sortfield=None, mask=None,
                 attrspec=None, attrlist=None, add_shortlist=None, q=None, additional_params=None, request_kwargs=None):
        """Fetches a representation of a list with the data of the direct descendants of the specified node
        :param node_id: start node ("root" of subtree)
        :param recursive: if True, include indirect children and the node given by `node_id`.
            False just fetches direct children.
        :param additional_params: query params which will be merged with params created from the method args.
            Params in `additional_params` overwrite other params!
        :param request_kwargs: theses args will be passed to the requests library
        :returns: wrapped result of the api call
        :rtype: NodeAPIResult
        """
        request = "/allchildren" if recursive else "/children"
        data = self._node(node_id, request, start, limit, type, sortfield, mask, attrspec, attrlist, add_shortlist, None, None,
                          q, additional_params, request_kwargs).json()
        self._raise_for_cached_failure(data)
        return NodeAPIResult(data)

    def allchildren(self, *args, **kwargs):
        """Shortcut for children(node_id, recursive=True, ...)
        """
        return self.children(*args, recursive=True, **kwargs)

    def children_shortlist(self, node_id, recursive=False, i0=None, i1=None, additional_params=None, request_kwargs=None):
        """Fetches only the "shortlist" of the children of `node_id`.
        The *shortlist* contains the node ids, names and types of the children
        :param recursive: if True, include indirect children and the node given by `node_id`.
            False just fetches direct children.
        :param additional_params: query params which will be merged with params created from the method args.
            Params in `additional_params` overwrite other params!
        :param request_kwargs: theses args will be passed to the requests library
        :rtype: Shortlist
        """
        request = "/allchildren" if recursive else "/children"
        data = self._node(node_id, request, limit=0, add_shortlist=True, i0=i0, i1=i1,
                          additional_params=additional_params, request_kwargs=request_kwargs).json()
        self._raise_for_cached_failure(data)
        return APIShortlist(data["result_shortlist"])

    def allchildren_shortlist(self, *args, **kwargs):
        """Shortcut for children_shortlist(node_id, recursive=True, ...)
        """
        return self.children_shortlist(*args, recursive=True, **kwargs)

    def parents(self, node_id, start=None, limit=None, type=None, sortfield=None, mask=None, attrspec=None,
                attrlist=None, add_shortlist=None, q=None, additional_params=None, request_kwargs=None):
        """Fetches a representation of a list with the data of the direct ascendants of the specified node.
        """
        request = "/parents"
        data = self._node(node_id, request, start, limit, type, sortfield, mask, attrspec, attrlist, add_shortlist,
                          None, None, q, additional_params, request_kwargs).json()
        self._raise_for_cached_failure(data)
        return NodeAPIResult(data)

    @property
    def default_additional_params(self):
        return self._default_additional_params

    @default_additional_params.setter
    def default_additional_params(self, additional_params):
        self._default_additional_params = additional_params


class MediatumAPIUrlMixin(object):

    """
    Sets a default URL and after_request handler for mediaTUM access
    """
    # override this if you like to use another instance by default
    BASE_URL = "http://localhost:8083/"
    SERVICE_PATH = "services/"
    EXPORT_PATH = "export/"

    raise_for_status = True

    def after_request(self, response):
        """Raises an exception if the HTTP status code indicates a failure"""
        if self.raise_for_status:
            response.raise_for_status()
        return response


class MediatumAPI(MediatumAPIAccessMixin, MediatumAPIUrlMixin, Url):

    """Access the mediaTUM API via this class. This client is stateless and doesn't save cookies!
    """

    def __init__(self, base_url=None, raise_for_status=True, **default_kwargs):
        self.raise_for_status = raise_for_status
        url = urljoin(base_url or self.BASE_URL, self.SERVICE_PATH)
        super(MediatumAPI, self).__init__(url, **default_kwargs)


class MediatumAPISession(MediatumAPIAccessMixin, MediatumAPIUrlMixin, SessionUrl):

    """Access the mediaTUM API via this class. This client is stateful and remembers cookies.
    """

    def __init__(self, base_url=None, raise_for_status=True, **default_kwargs):
        self.raise_for_status = raise_for_status
        url = urljoin(base_url or self.BASE_URL, self.SERVICE_PATH)
        super(MediatumAPISession, self).__init__(url, **default_kwargs)
        self.new_session()
