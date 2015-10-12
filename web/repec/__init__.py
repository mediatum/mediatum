import re
import logging

from datetime import datetime

from core import tree, config
from core.acl import AccessData
from core.users import getUser
from core.transition import httpstatus

from contenttypes.document import Document

from web.repec.redif import redif_encode_archive, redif_encode_series


log = logging.getLogger("repec")


_MATCH_REPEC_CODE = re.compile(r"^/repec/(?P<code>[\d\w]+)/((?P<code_check>[\d\w]+)(arch)|(seri))?.*$")


class RDFContent(object):

    def __init__(self, req):
        self.request = req

    def rdf(self):
        return ""

    def status(self):
        return httpstatus.HTTP_OK

    def respond(self):
        self.request.write(self.rdf())
        return self.status()


class HTMLContent(object):

    def __init__(self, req):
        self.request = req

    def html(self):
        return ""

    def status(self):
        return httpstatus.HTTP_OK

    def respond(self):
        self.request.write(self.html())
        return self.status()


class CollectionMixin(object):

    class __NoDefault__:
        pass

    def _get_inherited_attribute_value(self, node, attr, default=__NoDefault__):
        try:
            # try to get the attr from given node
            return node[attr]
        except KeyError:
            if node.id != 1:  # do not traverse up if we are on root node
                for parent in node.getParents():
                    try:
                        # go up in tree
                        return self._get_inherited_attribute_value(parent, attr, default)
                    except KeyError:
                        pass

        if default == self.__NoDefault__:
            # attr does not exist in node tree
            raise KeyError
        return default

    def _get_node_owner(self, node):
        try:
            node_owner = getUser(node["creator"])
            if node_owner:
                return node_owner
        except KeyError:
            pass
        try:
            node_owner = getUser(node["updateuser"])
            if node_owner:
                return node_owner
        except KeyError:
            pass

        return None

    def _get_document_pdf_url(self, node):
        root_url = self._get_root_url()

        if not node.has_object() or not isinstance(node, Document):
            log.info("Node %s has no PDF attached" % node.id)
            return None

        if "system.origname" in node and node["system.origname"] == "1":
            return u"%s/doc/%s/%s" % (root_url, node.id, node.getName())
        return u"%s/doc/%s/%s.pdf" % (root_url, node.id, node.id)

    def _get_root_url(self):
        if config.get("config.ssh") == "yes":
            return "https://%s" % config.get("host.name")
        return "http://%s" % config.get("host.name")

    def _get_root_collection(self):
        """
        Gets the root collection of the entire MediaTUM database.
        """
        return Node(self.request, self, tree.getRoot("collections"))

    def _get_active_collection(self):
        """
        Gets the active collection based on the request url. The RePEc code is used to
        choose the collection. Expects URL path in the format as follows:

        * `/repec/REPEC_CODE`
        * `/repec/REPEC_CODE/REPEC_CODEarch.rdf`
        * `/repec/REPEC_CODE/REPEC_CODEseri.rdf`
        * `/repec/REPEC_CODE/journl/...`
        * `/repec/REPEC_CODE/wpaper/...`
        """
        acl = AccessData(self.request)

        try:
            path_match = _MATCH_REPEC_CODE.match(self.request.fullpath)
            repec_code = path_match.group("code")
            repec_code_check = path_match.group("code_check")

            # if we have a check-code in the url, it must equal the code value
            if repec_code_check is not None and repec_code_check != repec_code:
                log.info("RePEc check code does not match")
                raise AttributeError

        except (IndexError, AttributeError):
            # path does not contain a repec code
            log.info("RePEc collection not found")
            self.status_code = httpstatus.HTTP_NOT_FOUND
            return None

        # try to load the node
        try:
            nodes = tree.getNodesByFieldValue(**{"repec.code": repec_code})
            if len(nodes) != 1:
                if len(nodes) > 1:
                    log.info("More than one collection with code %s" % repec_code)
                else:
                    log.info("No collection with code %s" % repec_code)

                raise tree.NoSuchNodeError
            node = nodes[0]
        except tree.NoSuchNodeError:
            # requested node not in DB, so set status to 404
            self.status_code = httpstatus.HTTP_NOT_FOUND
            return None

        if not acl.hasReadAccess(node):
            log.info("No access to collection with code %s" % repec_code)
            # requested node in DB but no access, so set status to 403
            self.status_code = httpstatus.HTTP_FORBIDDEN
            return None

        if node.type not in ("directory", "collection"):
            log.error("Node with code %s is not a collection" % repec_code)
            # requested node in DB and accessible, but not a collection type
            self.status_code = httpstatus.HTTP_INTERNAL_SERVER_ERROR
            return None

        # node exists and accessible
        self.status_code = httpstatus.HTTP_OK

        return Node(self.request, self, node)


class Node(RDFContent):

    def __init__(self, req, collection_content, node):
        super(Node, self).__init__(req)

        self.mapping = {}
        self.collection_content = collection_content
        self.node = node

    def __contains__(self, key):
        return self.node.__contains__(key)

    def __getitem__(self, key):
        return self.node.__getitem__(key)

    def __iter__(self):
        return self.node.__iter__()

    def __len__(self):
        return self.node.__len__()

    def __setitem__(self, key, value):
        return self.node.__setitem__(key, value)

    def __delitem__(self, key):
        return self.node.__delitem__(key)

    def apply_export_mapping(self, mask_name):
        mask = self.node.getMask(mask_name)
        attribute_mapping = {}

        # check if mask exists - disable mapping if it does not exist
        if not mask:
            self.mapping = {}
            return

        for mask_field in mask.getMaskFields():
            mapping_field = tree.getNode(mask_field.get("mappingfield"))
            attribute = tree.getNode(mask_field.get("attribute"))

            # skip if mapping or target attribute not found
            if None in (mapping_field, attribute):
                continue

            attribute_mapping[mapping_field.name] = self.get(attribute.name)

        self.mapping = attribute_mapping

    def get(self, key, default=None):
        # check if field in mapping
        if key in self.mapping:
            return self.mapping[key]

        # key in mapping not found - check if is node attribute
        if key in self:
            return self[key]

        # desired key not found - return default
        return default

    def get_all_child_nodes(self):
        return self.__get_child_nodes(lambda: list(set(tree.getAllContainerChildrenAbs(self.node, list()))))

    def get_all_child_nodes_by_field_value(self, **kwargs):
        return self.__get_child_nodes(lambda: list(set(tree.getAllContainerChildrenByFieldValueAbs(self.node, list(), **kwargs))))

    def get_child_nodes(self):
        return self.__get_child_nodes(self.node.getContentChildren)

    @staticmethod
    def _get_datetime_from_iso_8601(datestring):
        try:
            return datetime.strptime(datestring, "%Y-%m-%dT%H:%M:%S")
        except (TypeError, ValueError):
            return datetime(year=1970, month=1, day=1)

    def __get_child_nodes(self, fetch_function):
        acl = AccessData(self.request)

        node_ids = acl.filter(fetch_function())
        nodes = tree.NodeList(node_ids)

        return [Node(self.request, self.collection_content, n) for n in nodes]
