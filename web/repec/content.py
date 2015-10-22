import logging
import unicodedata
import re

from collections import OrderedDict

from mediatumtal import tal

from core import config
from core.transition import httpstatus

from web.repec import RDFContent, HTMLContent, CollectionMixin, Node
from web.repec.redif import redif_encode_archive, redif_encode_series, redif_encode_article, \
    redif_encode_paper, redif_encode_book


log = logging.getLogger("repec")


class HTMLCollectionContent(HTMLContent, CollectionMixin):
    """
    Lists the content of the RePEc collection as HTML.
    """

    def __init__(self, req):
        super(HTMLCollectionContent, self).__init__(req)

        self.root_collection = self._get_root_collection()
        self.active_collection = self._get_active_collection()
        self.child_collections = self._get_child_collections()

    def status(self):
        return self.status_code

    def html(self):
        if self.status_code != httpstatus.HTTP_OK:
            return ""

        repec_code = self.active_collection.get('repec.code')
        collection_links = []

        for collection in self.child_collections:
            child_repec_code = collection['repec.code']
            collection_links.append(("./%swpaper/" % child_repec_code, "%s Working Papers" % child_repec_code))
            collection_links.append(("./%sjournl/" % child_repec_code, "%s Journal" % child_repec_code))
            collection_links.append(("./%secbook/" % child_repec_code, "%s Books" % child_repec_code))

        return tal.processTAL({
            "items": [
                ("./%sarch.rdf" % repec_code, "%sarch.rdf" % repec_code),
                ("./%sseri.rdf" % repec_code, "%sseri.rdf" % repec_code),
            ] + collection_links
        }, file="web/repec/templates/directory_browsing.html", request=self.request)


class HTMLCollectionPaperContent(HTMLContent, CollectionMixin):
    """
    Lists the content of the RePEc working papers as HTML.
    """

    def __init__(self, req):
        super(HTMLCollectionPaperContent, self).__init__(req)

        self.root_collection = self._get_root_collection()
        self.active_collection = self._get_active_collection()

    def status(self):
        return self.status_code

    def html(self):
        if self.status_code != httpstatus.HTTP_OK:
            return ""

        return tal.processTAL({
            "items": [
                ("./papers.rdf", "papers.rdf"),
            ]
        }, file="web/repec/templates/directory_browsing.html", request=self.request)


class HTMLCollectionBookContent(HTMLContent, CollectionMixin):
    """
    Lists the content of the RePEc working papers as HTML.
    """

    def __init__(self, req):
        super(HTMLCollectionBookContent, self).__init__(req)

        self.root_collection = self._get_root_collection()
        self.active_collection = self._get_active_collection()

    def status(self):
        return self.status_code

    def html(self):
        if self.status_code != httpstatus.HTTP_OK:
            return ""

        return tal.processTAL({
            "items": [
                ("./books.rdf", "books.rdf"),
            ]
        }, file="web/repec/templates/directory_browsing.html", request=self.request)


class HTMLCollectionJournalContent(HTMLContent, CollectionMixin):
    """
    Lists the content of the RePEc working papers as HTML.
    """

    def __init__(self, req):
        super(HTMLCollectionJournalContent, self).__init__(req)

        self.root_collection = self._get_root_collection()
        self.active_collection = self._get_active_collection()

    def status(self):
        return self.status_code

    def html(self):
        if self.status_code != httpstatus.HTTP_OK:
            return ""

        return tal.processTAL({
            "items": [
                ("./journals.rdf", "journals.rdf"),
            ]
        }, file="web/repec/templates/directory_browsing.html", request=self.request)


class RDFCollectionContent(RDFContent, CollectionMixin):
    """
    Base class for collection RDF content.
    """

    def __init__(self, req, status_code):
        super(RDFCollectionContent, self).__init__(req)

        self.status_code = status_code

    def status(self):
        return self.status_code


class CollectionArchiveContent(RDFCollectionContent):
    """
    Class used for generating RDF of an archive.
    """

    def __init__(self, req):
        super(CollectionArchiveContent, self).__init__(req, httpstatus.HTTP_INTERNAL_SERVER_ERROR)

        self.root_collection = self._get_root_collection()
        self.active_collection = self._get_active_collection()

    def rdf(self):
        if self.status_code != httpstatus.HTTP_OK:
            return ""

        collection_node = self.active_collection.node
        collection_owner = self._get_node_owner(collection_node)
        root_domain = config.get("host.name")

        collection_data = {
            "Handle": "RePEc:%s" % collection_node["repec.code"],
            "URL": "%s/repec/%s/" % (self._get_root_url(), collection_node["repec.code"]),
            "Name": collection_node.unicode_name if collection_node.unicode_name else "Unknown name",
            "Maintainer-Name": "Unknown",
            "Maintainer-Email": "nomail@%s" % root_domain,
            "Restriction": None,
        }

        if collection_owner:
            collection_data.update({
                "Maintainer-Name": collection_owner.unicode_name,
                "Maintainer-Email": collection_owner["email"],
            })

        return redif_encode_archive(collection_data)


class CollectionSeriesContent(RDFCollectionContent):
    """
    Class used for generating RDF of a series.
    """

    def __init__(self, req):
        super(CollectionSeriesContent, self).__init__(req, httpstatus.HTTP_INTERNAL_SERVER_ERROR)

        self.root_collection = self._get_root_collection()
        self.active_collection = self._get_active_collection()
        self.child_collections = self._get_child_collections()

    @staticmethod
    def _slugify(val):
        # normalise non-ascii chars to an ascii representation
        if isinstance(val, unicode):
            val = unicodedata.normalize('NFKD', val).encode('ascii', 'ignore')

        val = re.sub('[^\w]', '', val).strip().lower()
        return val

    def rdf(self):
        if self.status_code != httpstatus.HTTP_OK:
            return ""

        series_rdfs = []
        collection_node = self.active_collection.node
        collection_owner = self._get_node_owner(collection_node)
        root_domain = config.get("host.name")
        repec_code = collection_node["repec.code"]
        provider_name = self._get_inherited_attribute_value(
            collection_node, "repec.provider", default="Unknown Provider",
        )
        provider_id = str(self._slugify(provider_name)).lower()

        for child_collection in self.child_collections:
            child_repec_code = child_collection['repec.code']

            collection_data = {
                "Name": "Working Papers",
                "Provider-Name": provider_name,
                "Maintainer-Name": "Unknown",
                "Maintainer-Email": "nomail@%s" % root_domain,
                "Type": "ReDIF-Paper",
                "Handle": "RePEc:%s:%swpaper" % (repec_code, child_repec_code),
            }

            if collection_owner:
                collection_data.update({
                    "Maintainer-Name": collection_owner.unicode_name,
                    "Maintainer-Email": collection_owner["email"],
                })

            wpaper_series_rdf = redif_encode_series(collection_data)

            collection_data = {
                "Name": "Journal",
                "Provider-Name": provider_name,
                "Provider-Institution": "RePEc:%s:%s" % (repec_code, provider_id),
                "Maintainer-Name": "Unknown",
                "Maintainer-Email": "nomail@%s" % root_domain,
                "Type": "ReDIF-Article",
                "Handle": "RePEc:%s:%sjournl" % (repec_code, child_repec_code),
            }

            if collection_owner:
                collection_data.update({
                    "Maintainer-Name": collection_owner.unicode_name,
                    "Maintainer-Email": collection_owner["email"],
                })

            journl_series_rdf = redif_encode_series(collection_data)

            collection_data = {
                "Name": "Books",
                "Provider-Name": provider_name,
                "Provider-Institution": "RePEc:%s:%s" % (repec_code, provider_id),
                "Maintainer-Name": "Unknown",
                "Maintainer-Email": "nomail@%s" % root_domain,
                "Type": "ReDIF-Book",
                "Handle": "RePEc:%s:%secbook" % (repec_code, child_repec_code),
            }

            if collection_owner:
                collection_data.update({
                    "Maintainer-Name": collection_owner.unicode_name,
                    "Maintainer-Email": collection_owner["email"],
                })

            ecbook_series_rdf = redif_encode_series(collection_data)

            series_rdfs.append("\n\n".join((wpaper_series_rdf, journl_series_rdf, ecbook_series_rdf)))

        return "\n\n".join(series_rdfs)


class CollectionJournalContent(RDFCollectionContent):
    """
    Class used for generating RDF of working papers.
    """

    def __init__(self, req):
        super(CollectionJournalContent, self).__init__(req, httpstatus.HTTP_INTERNAL_SERVER_ERROR)

        self.root_collection = self._get_root_collection()
        self.active_collection = self._get_active_collection()
        self.active_child_collection = self._get_active_child_collection()

    def rdf(self):
        if self.status_code != httpstatus.HTTP_OK:
            return ""

        child_nodes = self.active_child_collection.get_all_child_nodes_by_field_value(**{"repec.type": "ReDIF-Article"})
        repec_code = self.active_collection.node["repec.code"]
        rdf_content = []

        for child_node in child_nodes:
            child_node.apply_export_mapping("repec-export-article")
            child_node_repec_code = self._get_inherited_attribute_value(child_node, 'repec.code')

            # skip file if mandatory fields are not present
            if None in (child_node.get("Author-Name"), child_node.get("Title")):
                continue

            creation_date = Node._get_datetime_from_iso_8601(child_node.get("Creation-Date"))
            child_year = Node._get_datetime_from_iso_8601(child_node.get("Year"))
            file_url = self._get_document_pdf_url(child_node.node)

            file_data = {
                "_author_1": OrderedDict([
                    ("Author-Name", child_node.get("Author-Name")),
                    ("Author-Name-First", child_node.get("Author-Name-First")),
                    ("Author-Name-Last", child_node.get("Author-Name-Last")),
                    ("Author-Email", child_node.get("Author-Email")),
                    ("Author-Workplace-Name", child_node.get("Author-Workplace-Name")),
                ]),
                "_file_1": OrderedDict([
                    ("File-URL", file_url),
                    ("File-Format", child_node.get("File-Format", "application/pdf")),
                    ("File-Function", "%s, %s" % (child_node.get("File-Function"), child_node.get("Year")) \
                        if child_node.get("File-Function") and child_node.get("Year") else None),
                ]) if file_url else None,
                "Title": child_node.get("Title"),
                "Abstract": child_node.get("Abstract"),
                "Pages": child_node.get("Pages"),
                "Volume": child_node.get("Volume"),
                "Issue": child_node.get("Issue"),
                "Classification-JEL": child_node.get("Classification-JEL"),
                "Number": child_node.node.id,
                "Year": "%04d" % child_year.year if child_node.get("Year") else None,
                "Keywords": child_node.get("Keywords"),
                "Journal": child_node.get("Journal"),
                "Creation-Date": "%04d-%02d-%02d" % (creation_date.year, creation_date.month, creation_date.day),
                "Handle": "RePEc:%s:%sjournl:%s" % (repec_code, child_node_repec_code, child_node.node.id),
            }
            rdf_content.append(redif_encode_article(file_data))

        return "\n\n".join(rdf_content)


class CollectionPaperContent(RDFCollectionContent):
    """
    Class used for generating RDF of journals.
    """

    def __init__(self, req):
        super(CollectionPaperContent, self).__init__(req, httpstatus.HTTP_INTERNAL_SERVER_ERROR)

        self.root_collection = self._get_root_collection()
        self.active_collection = self._get_active_collection()
        self.active_child_collection = self._get_active_child_collection()

    def rdf(self):
        if self.status_code != httpstatus.HTTP_OK:
            return ""

        child_nodes = self.active_child_collection.get_all_child_nodes_by_field_value(**{"repec.type": "ReDIF-Paper"})
        repec_code = self.active_collection.node["repec.code"]
        rdf_content = []

        for child_node in child_nodes:
            child_node.apply_export_mapping("repec-export-paper")
            child_node_repec_code = self._get_inherited_attribute_value(child_node, 'repec.code')

            # skip file if mandatory fields are not present
            if None in (child_node.get("Author-Name"), child_node.get("Title")):
                continue

            creation_date = Node._get_datetime_from_iso_8601(child_node.get("Creation-Date"))
            update_date = Node._get_datetime_from_iso_8601(child_node.get("Revision-Date"))
            file_url = self._get_document_pdf_url(child_node.node)

            file_data = {
                "_author_1": OrderedDict([
                    ("Author-Name", child_node.get("Author-Name")),
                    ("Author-Name-First", child_node.get("Author-Name-First")),
                    ("Author-Name-Last", child_node.get("Author-Name-Last")),
                    ("Author-Email", child_node.get("Author-Email")),
                    ("Author-Workplace-Name", child_node.get("Author-Workplace-Name")),
                ]),
                "_file_1": OrderedDict([
                    ("File-URL", file_url),
                    ("File-Format", child_node.get("File-Format", "application/pdf")),
                    ("File-Function", "%s, %s" % (child_node.get("File-Function"), child_node.get("Year")) \
                        if child_node.get("File-Function") and child_node.get("Year") else None),
                ]) if file_url else None,
                "Title": child_node.get("Title"),
                "Abstract": child_node.get("Abstract"),
                "Length": "%s pages" % child_node.get("Length") if child_node.get("Length") else None,
                "Language": child_node.get("Language"),
                "Classification-JEL": child_node.get("Classification-JEL"),
                "Creation-Date": "%04d-%02d-%02d" % (creation_date.year, creation_date.month, creation_date.day),
                "Revision-Date": "%04d-%02d-%02d" % (update_date.year, update_date.month, update_date.day),
                "Publication-Status": "Published by %s" % child_node.get("Publication-Status") \
                    if child_node.get("Publication-Status") else None,
                "Number": child_node.node.id,
                "Keywords": child_node.get("Keywords"),
                "Handle": "RePEc:%s:%swpaper:%s" % (repec_code, child_node_repec_code, child_node.node.id),
            }
            rdf_content.append(redif_encode_paper(file_data))

        return "\n\n".join(rdf_content)


class CollectionBookContent(RDFCollectionContent):
    """
    Class used for generating RDF of books.
    """

    def __init__(self, req):
        super(CollectionBookContent, self).__init__(req, httpstatus.HTTP_INTERNAL_SERVER_ERROR)

        self.root_collection = self._get_root_collection()
        self.active_collection = self._get_active_collection()
        self.active_child_collection = self._get_active_child_collection()

    def rdf(self):
        if self.status_code != httpstatus.HTTP_OK:
            return ""

        child_nodes = self.active_child_collection.get_all_child_nodes_by_field_value(**{"repec.type": "ReDIF-Book"})
        repec_code = self.active_collection.node["repec.code"]
        rdf_content = []

        for child_node in child_nodes:
            child_node.apply_export_mapping("repec-export-book")
            child_node_repec_code = self._get_inherited_attribute_value(child_node, 'repec.code')

            # skip file if mandatory fields are not present
            if None in (child_node.get("Editor-Name"), child_node.get("Title")):
                continue

            creation_date = Node._get_datetime_from_iso_8601(child_node.get("Creation-Date"))
            file_url = self._get_document_pdf_url(child_node.node)

            file_data = {
                "_editor_1": OrderedDict([
                    ("Editor-Name", child_node.get("Editor-Name")),
                    ("Editor-Name-First", child_node.get("Editor-Name-First")),
                    ("Editor-Name-Last", child_node.get("Editor-Name-Last")),
                    ("Editor-Email", child_node.get("Editor-Email")),
                    ("Editor-Workplace-Name", child_node.get("Editor-Workplace-Name")),
                ]),
                "_file_1": OrderedDict([
                    ("File-URL", file_url),
                    ("File-Format", child_node.get("File-Format", "application/pdf")),
                    ("File-Function", "%s, %s" % (child_node.get("File-Function"), child_node.get("Year")) \
                        if child_node.get("Type") and child_node.get("Year") else None),
                ]) if file_url else None,
                "Title": child_node.get("Title"),
                "Abstract": child_node.get("Abstract"),
                "Language": child_node.get("Language"),
                "Pages": child_node.get("Pages"),
                "Volume": child_node.get("Volume"),
                "Issue": child_node.get("Issue"),
                "Classification-JEL": child_node.get("Classification-JEL"),
                "Creation-Date": "%04d-%02d-%02d" % (creation_date.year, creation_date.month, creation_date.day),
                "Publication-Status": "Published by %s" % child_node.get("Publication-Status") \
                    if child_node.get("Publication-Status") else None,
                "Number": child_node.node.id,
                "Keywords": child_node.get("Keywords"),
                "Handle": "RePEc:%s:%secbook:%s" % (repec_code, child_node_repec_code, child_node.node.id),
            }
            rdf_content.append(redif_encode_book(file_data))

        return "\n\n".join(rdf_content)
