from typing import List
import requests
import logging

from geonoderest.geonodeobject import GeonodeObjectHandler
from geonoderest.geonodetypes import GeonodeCmdOutListKey, GeonodeCmdOutDictKey
from geonoderest.exceptions import GeoNodeRestException

SUPPORTED_METADATA_TYPES: List[str] = [
    "Atom",
    "DIF",
    "Dublin Core",
    "FGDC",
    "ISO",
]
DEFAULT_METADATA_TYPE: str = "ISO"


class GeonodeResourceHandler(GeonodeObjectHandler):
    ENDPOINT_NAME = JSON_OBJECT_NAME = "resources"
    SINGULAR_RESOURCE_NAME = "resource"

    LIST_CMDOUT_HEADER = [
        GeonodeCmdOutListKey(key="pk"),
        GeonodeCmdOutListKey(key="title"),
        GeonodeCmdOutDictKey(key=["owner", "username"]),
        GeonodeCmdOutListKey(key="resource_type"),
        GeonodeCmdOutListKey(key="state"),
        GeonodeCmdOutListKey(key="detail_url"),
    ]

    def cmd_metadata(
        self, pk: int, metadata_type: str = DEFAULT_METADATA_TYPE, **kwargs
    ):
        """show metadata on cmdline

        Args:
            pk (int): pk id of the resource to get the metadata from
            metadata_type (str, optional): metadatatype to get metadata in. Must be in SUPPORTED_METADATA_TYPES
        """
        r = self.metadata(pk=pk, metadata_type=metadata_type, **kwargs)
        if r is None:
            logging.warning("metadata download failed ... ")
            return None
        print(r.text)

    def metadata(
        self, pk: int, metadata_type: str = DEFAULT_METADATA_TYPE, **kwargs
    ) -> requests.models.Response:
        """download metadata for a resource in a specified format

        Args:
            pk (int): pk id of the resource to get the metadata from
            metadata_type (str, optional): metadatatype to get metadata in. Must be in SUPPORTED_METADATA_TYPES
        Raises:
            KeyError: if metadata_type is not in SUPPORTED_METADATA_TYPES
        Returns:
            response (object): requests response obj of metadata
        """
        r = self.http_get(endpoint=f"resources/{pk}")["resource"]

        link: str
        link = [m for m in r["links"] if m["name"] == metadata_type][0]["url"]
        return self.http_get_download(link)
