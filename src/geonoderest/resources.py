from typing import List, Dict, Optional
import requests
import logging

from geonoderest.geonodeobject import GeonodeObjectHandler
from geonoderest.geonodetypes import GeonodeCmdOutListKey, GeonodeCmdOutDictKey
from geonoderest.executionrequest import GeonodeExecutionRequestHandler
from geonoderest.cmdprint import print_json, show_list
from geonoderest.identifier import ANY_RESOURCE_TYPE
from geonoderest.exceptions import GeonodeUsageError
from geonoderest.exitcodes import EXIT_FAILED, EXIT_OK, EXIT_USAGE
from geonoderest.validate import (
    SchemaLoadError,
    build_validator,
    collect_errors,
    load_schema,
)

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
    # these verbs span every resource type, so any uuid resolves
    UUID_RESOURCE_TYPE = ANY_RESOURCE_TYPE

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
        self, pk, metadata_type: str = DEFAULT_METADATA_TYPE, **kwargs
    ) -> int:
        """show metadata on cmdline

        Args:
            pk: pk or uuid of the resource to get the metadata from
            metadata_type (str, optional): metadatatype to get metadata in. Must be in SUPPORTED_METADATA_TYPES

        Returns:
            int: EXIT_OK, or EXIT_FAILED when the metadata could not be fetched
        """
        pk = self.__resolve_identifier__(pk)
        r = self.metadata(pk=pk, metadata_type=metadata_type, **kwargs)
        if r is None:
            logging.error("metadata download failed ... ")
            return EXIT_FAILED
        print(r.text)
        return EXIT_OK

    def metadata(
        self, pk: int, metadata_type: str = DEFAULT_METADATA_TYPE, **kwargs
    ) -> Optional[requests.models.Response]:
        """download metadata for a resource in a specified format

        Args:
            pk (int): pk id of the resource to get the metadata from
            metadata_type (str, optional): metadatatype to get metadata in. Must be in SUPPORTED_METADATA_TYPES
        Returns:
            Optional[Response]: the metadata response, or None when the resource
                could not be fetched or carries no link of that type - reported
                rather than raised, so cmd_metadata can turn it into an exit code
        """
        response = self.http_get(endpoint=f"resources/{pk}")
        if response is None:
            return None
        r = response.get("resource")
        if r is None:
            logging.error(f"unexpected API response for resource {pk} ...")
            return None

        links = [m for m in r.get("links", []) if m.get("name") == metadata_type]
        if not links:
            logging.error(
                f"resource {pk} has no {metadata_type} metadata link - "
                f"available: {', '.join(m.get('name', '?') for m in r.get('links', []))}"
            )
            return None
        return self.http_get_download(links[0]["url"])

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

    def cmd_validate(self, pk: str, json_schema: Optional[str] = None, **kwargs) -> int:
        """validate metadata of one or more objects against a JSON Schema

        Args:
            pk (str): pk of the object(s), as single, range '1-5' or list '1,2,3'
            json_schema (str): path to a JSON Schema file, or a http(s) url
                serving one. Relative ``$ref``s are resolved against it.

        Returns:
            int: EXIT_OK when everything validated, EXIT_FAILED when an object
                violated the schema or could not be fetched, EXIT_USAGE when the
                schema itself is missing or unusable
        """
        if not json_schema:
            logging.error("--json_schema is required")
            return EXIT_USAGE

        try:
            schema = load_schema(json_schema)
            validator = build_validator(schema, json_schema)
            pks = self.__parse_pk_string__(pk)
        except (SchemaLoadError, GeonodeUsageError) as e:
            logging.error(str(e))
            return EXIT_USAGE

        report: List[Dict] = []
        unreachable: List[int] = []

        for _pk in pks:
            try:
                errors = self.validate(pk=_pk, validator=validator, **kwargs)
            except SchemaLoadError as e:
                # $refs resolve lazily, so an unusable schema only shows up here
                logging.error(str(e))
                return EXIT_USAGE
            if errors is None:
                logging.error(f"could not fetch {self.SINGULAR_RESOURCE_NAME} {_pk}")
                unreachable.append(_pk)
                continue
            report.append({"pk": _pk, "valid": len(errors) == 0, "errors": errors})

        if kwargs.get("json"):
            print_json(report)
        else:
            self.__print_validation_report__(report)

        if unreachable or any(not entry["valid"] for entry in report):
            return EXIT_FAILED
        return EXIT_OK

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
