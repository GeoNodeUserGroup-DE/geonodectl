import os
import mimetypes
from pathlib import Path
from typing import List, Optional, Dict

from src.geonodetypes import GeonodeCmdOutListKey, GeonodeCmdOutDictKey
from src.cmdprint import show_list
from src.resources import GeonodeResourceHandler
from src.geonodetypes import GeonodeHTTPFile


class GeonodeDocumentsHandler(GeonodeResourceHandler):
    RESOURCE_TYPE = "documents"
    SINGULAR_RESOURCE_NAME = "document"

    LIST_CMDOUT_HEADER = [
        GeonodeCmdOutListKey(key="pk"),
        GeonodeCmdOutListKey(key="title"),
        GeonodeCmdOutDictKey(key=["owner", "username"]),
        GeonodeCmdOutListKey(key="date"),
        GeonodeCmdOutListKey(key="is_approved"),
        GeonodeCmdOutListKey(key="is_published"),
        GeonodeCmdOutListKey(key="resource_type"),
        GeonodeCmdOutListKey(key="detail_url"),
    ]

    def cmd_upload(
        self,
        title: str,
        file_path: Path,
        metadata_only: bool = False,
        charset: str = "UTF-8",
        **kwargs
    ):
        """upload data and show them on the cmdline

        Args:
            title (str): title of the new dataset
            file_path (Path): Path to the file to upload.
            charset (str, optional): charset of data Defaults to "UTF-8".
            metadata_only (bool, optional): set upload as metadata_only
        """
        r = self.upload(
            title=title,
            file_path=file_path,
            metadata_only=metadata_only,
            charset=charset,
            **kwargs
        )
        list_items = [
            ["name", r["title"]],
            ["state", r["state"]],
            ["subtype", r["subtype"]],
            ["mimetype", r["mime_type"]],
            ["detail-urk", r["detail_url"]],
            ["download-url", r["href"]],
        ]
        if kwargs["json"]:
            self.print_json(r)

        else:
            show_list(values=list_items, headers=["key", "value"])

    def upload(
        self,
        title: str,
        file_path: Path,
        charset: str = "UTF-8",
        metadata_only: bool = False,
        **kwargs
    ) -> Dict:
        """upload a document to geonode

        Args:
            title (str): title of the document
            file_path (Path): file to upload
            charset (str, optional): charset. Defaults to "UTF-8".
            metadata_only (bool, optional):  set upload as metadata_only. Defaults to False.

        Raises:
            FileNotFoundError: raises file not found if the given filepath is not accessable

        Returns:
            Dict: returns json response from geonode as dict
        """

        document_path: Path = file_path
        if not document_path.exists():
            raise FileNotFoundError

        params = {
            # layer permissions
            "permissions": '{ "users": {"AnonymousUser": ["view_resourcebase"]} , "groups":{}}',
            "title": title,
            "abstract": kwargs["abstract"] if "abstract" in kwargs else "",
            "charset": charset,
            "metadata_only": metadata_only,
        }

        files: List[GeonodeHTTPFile]
        content_length: int = os.path.getsize(document_path)
        mimetype: Optional[str] = mimetypes.guess_type(document_path)[0]
        if mimetype:
            files = [
                ("doc_file", (document_path.name, open(document_path, "rb"), mimetype)),
            ]
        else:
            files = [
                ("doc_file", (document_path.name, open(document_path, "rb"))),
            ]

        return self.http_post(
            endpoint="documents",
            files=files,
            params=params,
            content_length=content_length,
        )["document"]
