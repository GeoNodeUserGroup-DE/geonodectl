from typing import List, Dict, Optional
import requests
import logging
import sys

from geonoderest.geonodeobject import GeonodeObjectHandler
from geonoderest.geonodetypes import GeonodeCmdOutListKey, GeonodeCmdOutDictKey
from geonoderest.exceptions import GeoNodeRestException
from geonoderest.executionrequest import GeonodeExecutionRequestHandler
from geonoderest.cmdprint import print_json, show_list
from geonoderest.validate import (
    SchemaLoadError,
    build_validator,
    collect_errors,
    load_schema,
)

# exit codes used by cmd_validate
VALIDATE_EXIT_OK: int = 0
VALIDATE_EXIT_INVALID: int = 1
VALIDATE_EXIT_ERROR: int = 2

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

    def delete(self, pk: int, **kwargs):
        return self.http_delete(endpoint=f"resources/{pk}/delete")

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

    def validate(self, pk: int, validator, **kwargs) -> Optional[List[Dict]]:
        """validate a single object's metadata against a prepared validator

        Library method: it neither prints nor exits, so it stays usable from
        ``geonoderest`` as a library (see issue #69).

        Args:
            pk (int): pk of the object to validate
            validator: a validator from ``geonoderest.validate.build_validator``

        Returns:
            List[Dict]: violations, empty when the object is valid, or None when
                the object could not be fetched at all
        """
        obj = self.get(pk=pk, **kwargs)
        if obj is None:
            return None
        return collect_errors(validator, obj)

    def cmd_validate(self, pk: str, json_schema: str, **kwargs):
        """validate metadata of one or more objects against a JSON Schema

        Args:
            pk (str): pk of the object(s), as single, range '1-5' or list '1,2,3'
            json_schema (str): path to a JSON Schema file

        Exits:
            0 when everything validated, 1 when an object violated the schema,
            2 when validation could not be carried out at all
        """
        try:
            schema = load_schema(json_schema)
            validator = build_validator(schema, json_schema)
        except SchemaLoadError as e:
            logging.error(str(e))
            sys.exit(VALIDATE_EXIT_ERROR)

        report: List[Dict] = []
        unreachable: List[int] = []

        for _pk in self.__parse_pk_string__(pk):
            try:
                errors = self.validate(pk=_pk, validator=validator, **kwargs)
            except SchemaLoadError as e:
                # $refs resolve lazily, so an unusable schema only shows up here
                logging.error(str(e))
                sys.exit(VALIDATE_EXIT_ERROR)
            if errors is None:
                logging.error(f"could not fetch {self.SINGULAR_RESOURCE_NAME} {_pk}")
                unreachable.append(_pk)
                continue
            report.append({"pk": _pk, "valid": len(errors) == 0, "errors": errors})

        if kwargs.get("json"):
            print_json(report)
        else:
            self.__print_validation_report__(report)

        if unreachable:
            sys.exit(VALIDATE_EXIT_ERROR)
        if any(not entry["valid"] for entry in report):
            sys.exit(VALIDATE_EXIT_INVALID)

    def __print_validation_report__(self, report: List[Dict]):
        """print a human readable validation report on the cmdline"""
        for entry in report:
            noun = f"{self.SINGULAR_RESOURCE_NAME} {entry['pk']}"
            if entry["valid"]:
                print(f"{noun}: valid")
                continue

            errors = entry["errors"]
            print(f"{noun}: invalid, {len(errors)} violation(s)")
            show_list(
                headers=["path", "keyword", "message"],
                values=[[e["path"], e["keyword"], e["message"]] for e in errors],
            )
            print()

        invalid = sum(1 for entry in report if not entry["valid"])
        print(
            f"{len(report)} checked, {len(report) - invalid} valid, {invalid} invalid"
        )

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
