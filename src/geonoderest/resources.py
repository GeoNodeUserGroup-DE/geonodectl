from typing import List, Dict, Optional
import requests
import logging

from geonoderest.geonodeobject import GeonodeObjectHandler
from geonoderest.geonodetypes import GeonodeCmdOutListKey, GeonodeCmdOutDictKey
from geonoderest.exceptions import GeoNodeRestException
from geonoderest.executionrequest import GeonodeExecutionRequestHandler

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

    def delete_async(self, pk: int) -> Optional[Dict]:
        """Asynchronous delete via ``DELETE /api/v2/resources/{pk}/delete``.

        Unlike :meth:`delete` (which hits the synchronous endpoint), this
        returns an async receipt — ``{status, execution_id, status_url}`` —
        suitable for passing to :meth:`wait_for_completion`. Use this when
        the caller needs to confirm the deletion completed (e.g. before
        relying on it in a downstream assertion).
        """
        return self.http_delete(endpoint=f"{self.ENDPOINT_NAME}/{pk}/delete")

    def wait_for_completion(
        self,
        exec_id: str,
        poll_interval: int = 2,
        timeout: int = 180,
        on_poll=None,
    ) -> Dict:
        """Poll an async resource operation (delete, copy, …) to completion.

        Delegates to :class:`GeonodeExecutionRequestHandler` so the polling
        behavior is consistent across uploads, deletes, and permission
        changes.
        """
        handler = GeonodeExecutionRequestHandler(env=self.gn_credentials)
        return handler.wait_for_completion(
            exec_id=exec_id,
            poll_interval=poll_interval,
            timeout=timeout,
            on_poll=on_poll,
        )
