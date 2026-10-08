import os
import re
import mimetypes
import warnings
from pathlib import Path
from typing import IO, List, Optional, Dict
import logging

from geonoderest.geonodetypes import GeonodeCmdOutListKey, GeonodeCmdOutDictKey
from geonoderest.cmdprint import show_list, print_json
from geonoderest.exitcodes import EXIT_FAILED, EXIT_OK, EXIT_USAGE
from geonoderest.resources import GeonodeResourceHandler
from geonoderest.geonodetypes import GeonodeHTTPFile

DEPRECATION_REASON = (
    "creating documents through POST api/v2/documents is deprecated: GeoNode "
    "dropped document creation from that endpoint in 5.0.3 in favour of the "
    "documents/upload form view, and geonodectl will stop using it once GeoNode "
    "older than 5.0.3 goes unsupported (#176). Please upgrade GeoNode."
)


class GeonodeDocumentsHandler(GeonodeResourceHandler):
    ENDPOINT_NAME = JSON_OBJECT_NAME = "documents"
    SINGULAR_RESOURCE_NAME = "document"
    UUID_RESOURCE_TYPE = "document"

    #: path of the form view that creates documents, relative to the geonode
    #: base url - it is a plain django view, not part of the rest api
    UPLOAD_FORM_PATH = "documents/upload"

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
        file_path: Path,
        title: Optional[str] = None,
        metadata_only: bool = False,
        charset: str = "UTF-8",
        **kwargs,
    ) -> int:
        """upload data and show them on the cmdline

        Args:
            file_path (Path): Path to the file to upload.
            title (Optional[str], optional): title of the document. Defaults to
                  the file name.
            charset (str, optional): charset of data Defaults to "UTF-8".
            metadata_only (bool, optional): set upload as metadata_only

        Returns:
            int: EXIT_OK, EXIT_FAILED when the upload failed, EXIT_USAGE when
                the file does not exist
        """
        try:
            r = self.upload(
                file_path=file_path,
                title=title,
                metadata_only=metadata_only,
                charset=charset,
                **kwargs,
            )
        except OSError as e:
            # not just FileNotFoundError - a directory or an unreadable file too
            logging.error(f"could not read {file_path}: {e}")
            return EXIT_USAGE
        if r is None:
            logging.error("upload failed ... ")
            return EXIT_FAILED

        list_items = [
            ["name", r.get("title")],
            ["state", r.get("state")],
            ["subtype", r.get("subtype")],
            ["mimetype", r.get("mime_type")],
            ["detail-urk", r.get("detail_url")],
            ["download-url", r.get("href")],
        ]
        if kwargs["json"]:
            print_json(r)

        else:
            show_list(values=list_items, headers=["key", "value"])
        return EXIT_OK

    def upload(
        self,
        file_path: Path,
        title: Optional[str] = None,
        charset: str = "UTF-8",
        metadata_only: bool = False,
        **kwargs,
    ) -> Optional[Dict]:
        """upload a document to geonode

        Which endpoint creates a document depends on the GeoNode version, so the
        choice is made from what the api advertises rather than from a version
        number: GeoNode 5.0.3 dropped POST from the ``documents`` endpoint
        (upstream #14224) in favour of the ``documents/upload`` form view, while
        4.x and 5.0.0 - 5.0.2 only have the api endpoint - they predate the basic
        auth middleware that lets a non-api view authenticate an api client
        (#175). Dropping the older path once those versions go unsupported is
        #176.

        Args:
            file_path (Path): file to upload
            title (Optional[str], optional): title of the document. Defaults to
                  the file name, as geonode itself does.
            charset (str, optional): accepted for backwards compatibility and
                  unused - a document has no charset in either endpoint.
            metadata_only (bool, optional):  set upload as metadata_only. Defaults to False.

        Raises:
            FileNotFoundError: raises file not found if the given filepath is not accessable

        Returns:
            Optional[Dict]: returns json response from geonode as dict
        """

        document_path: Path = file_path
        if not document_path.exists():
            raise FileNotFoundError

        if title is None:
            title = document_path.name

        # the file is opened before anything goes over the wire, so that an
        # unreadable path is a usage error rather than a failed request
        with open(document_path, "rb") as handle:
            allowed = self.http_allowed_methods(self.ENDPOINT_NAME)
            if allowed is not None and "POST" not in allowed:
                return self.__upload_via_form_view__(
                    document_path=document_path,
                    handle=handle,
                    title=title,
                    metadata_only=metadata_only,
                )
            if allowed is None:
                # nothing was advertised, so the api endpoint is a guess rather
                # than a statement about the server - not worth a warning
                logging.debug(
                    "could not tell which methods this geonode allows on "
                    f"{self.ENDPOINT_NAME}, trying the api endpoint ..."
                )
            else:
                # DeprecationWarning for library callers, who can filter it, and
                # a log line for the cmdline, where it would be hidden by default
                warnings.warn(DEPRECATION_REASON, DeprecationWarning, stacklevel=2)
                logging.warning(DEPRECATION_REASON)
            return self.__upload_via_api__(
                document_path=document_path,
                handle=handle,
                title=title,
                metadata_only=metadata_only,
            )

    def __upload_via_api__(
        self,
        document_path: Path,
        handle: IO[bytes],
        title: str,
        metadata_only: bool,
    ) -> Optional[Dict]:
        """create a document through POST api/v2/documents (GeoNode < 5.0.3)

        The fields go out as ``data``, not as ``json``: requests overwrites a
        json body with the multipart one, so everything next to the file used to
        be dropped on the way out - which is why --metadata-only never had any
        effect.
        """
        return self.__unwrap__(
            self.http_post(
                endpoint=self.ENDPOINT_NAME,
                files=self.__doc_file__(document_path, handle),
                data={"title": title, "metadata_only": metadata_only},
                content_length=os.path.getsize(document_path),
            )
        )

    def __upload_via_form_view__(
        self,
        document_path: Path,
        handle: IO[bytes],
        title: str,
        metadata_only: bool,
    ) -> Optional[Dict]:
        """create a document through POST documents/upload (GeoNode >= 5.0.3)

        The view answers with the detail url of what it created and nothing else,
        so the pk has to be read back out of that url and the document fetched
        before it can be reported like the api endpoint's response.
        """
        r = self.http_post(
            endpoint=self.UPLOAD_FORM_PATH,
            form=True,
            # without this the view answers 302 to the detail page, not json
            params={"no__redirect": "true"},
            data={"title": title},
            files=self.__doc_file__(document_path, handle),
        )
        if r is None:
            return None
        if r.get("success") is not True:
            logging.error(f"geonode rejected the upload: {r.get('message', r)}")
            return None

        pk = self.__pk_from_detail_url__(r.get("url"))
        if pk is None:
            logging.error(f"could not tell which document was created from: {r} ...")
            return None

        document = self.get(pk=pk)
        if not metadata_only:
            return document

        # The upload form has no metadata_only field, so it is set afterwards -
        # and the document has to be read back before that happens: geonode
        # filters a metadata_only document out of the documents endpoint
        # altogether, which then answers 404 to a GET and to a further PATCH.
        # What the PATCH returns is the authority on the result; the untouched
        # document is only there in case it comes back without a body.
        patched = self.patch(pk=pk, json_content={"metadata_only": True})
        if patched is None:
            logging.error(f"could not set metadata_only on document {pk} ...")
            return None
        return patched.get(self.SINGULAR_RESOURCE_NAME, document)

    @staticmethod
    def __doc_file__(document_path: Path, handle: IO[bytes]) -> List[GeonodeHTTPFile]:
        """the document as the single multipart file part both endpoints expect"""
        mimetype: Optional[str] = mimetypes.guess_type(document_path)[0]
        if mimetype:
            return [("doc_file", (document_path.name, handle, mimetype))]
        return [("doc_file", (document_path.name, handle))]

    @staticmethod
    def __pk_from_detail_url__(url: Optional[str]) -> Optional[int]:
        """pk out of a resource detail url, e.g. /catalogue/#/document/42"""
        if not url:
            return None
        match = re.search(r"(\d+)/?$", url)
        return int(match.group(1)) if match else None

    def __unwrap__(self, r: Optional[Dict]) -> Optional[Dict]:
        """the document out of an api response that wraps it, when there is one"""
        if r is None:
            return None
        return r[self.SINGULAR_RESOURCE_NAME]
