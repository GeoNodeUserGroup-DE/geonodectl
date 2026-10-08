from difflib import get_close_matches
import logging
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin

from geonoderest.apiconf import GeonodeApiConf
from geonoderest.cmdprint import print_json, print_validation_report, show_list
from geonoderest.exceptions import (
    GeoNodeRestException,
    GeonodeUsageError,
    MetadataFieldError,
)
from geonoderest.exitcodes import EXIT_FAILED, EXIT_OK, EXIT_USAGE
from geonoderest.identifier import ANY_RESOURCE_TYPE
from geonoderest.jsonsource import JsonSourceError, load_json_source
from geonoderest.metadatafields import (
    FieldOp,
    apply_ops,
    check_payload_keys,
    choices_of,
    flatten_errors,
    is_reference,
    lookup_paths,
    lookup_url,
    needs_current_instance,
    parse_field_expr,
    payload_schema,
    resolve_property,
    types_of,
    for_validation,
)
from geonoderest.rest import GeonodeRest
from geonoderest.validate import SchemaLoadError, build_validator, collect_errors

NOT_FOUND = 404
UNPROCESSABLE = 422


class GeonodeMetadataHandler(GeonodeRest):
    """GeoNode 5's json-schema metadata api, ``/api/v2/metadata`` (#174)."""

    ENDPOINT_NAME = "metadata"
    UUID_RESOURCE_TYPE = ANY_RESOURCE_TYPE

    #: never written through this api: it replaces the whole list of outgoing
    #: links, deleting any it is not given, so an edit of one link would be a
    #: read-modify-write racing other edits - ``linked-resources`` adds and
    #: deletes single links atomically, and works on GeoNode 4 too
    LINKED_RESOURCES_FIELD = "linkedresources"

    def __init__(self, env: GeonodeApiConf) -> None:
        super().__init__(env)
        self._schemas: Dict[Optional[str], Dict] = {}

    @staticmethod
    def __params__(lang: Optional[str]) -> Dict:
        return {"lang": lang} if lang else {}

    @property
    def schema_url(self) -> str:
        return f"{self.url}{self.ENDPOINT_NAME}/schema"

    @staticmethod
    def __missing_api__() -> GeoNodeRestException:
        return GeoNodeRestException(
            "this GeoNode has no metadata api - it needs GeoNode 5 or newer ..."
        )

    # library ------------------------------------------------------------------

    def schema(self, lang: Optional[str] = None) -> Optional[Dict]:
        """The metadata json schema, fetched once per handler and language.

        Raises:
            GeoNodeRestException: the server has no metadata api, or no schema
        """
        if lang not in self._schemas:
            r = self.http_get(
                f"{self.ENDPOINT_NAME}/schema",
                params=self.__params__(lang),
                accept=(NOT_FOUND,),
            )
            if r is None:
                return None
            status, body = r
            if status == NOT_FOUND:
                raise self.__missing_api__()
            if "properties" not in body:
                raise GeoNodeRestException(
                    f"the metadata api returned no schema: {body}"
                )
            self._schemas[lang] = body
        return self._schemas[lang]

    def get(self, pk: int, lang: Optional[str] = None) -> Optional[Dict]:
        """The metadata of a resource as an instance of the schema.

        Raises:
            GeoNodeRestException: the server has no metadata api
        """
        r = self.http_get(
            f"{self.ENDPOINT_NAME}/instance/{pk}",
            params=self.__params__(lang),
            accept=(NOT_FOUND,),
        )
        if r is None:
            return None
        status, body = r
        if status == NOT_FOUND:
            # the api answers a missing resource with a json message; a missing
            # route gets django's html page, which comes back as {}
            if not body:
                raise self.__missing_api__()
            logging.error(f"no resource {pk}: {body.get('message', body)} ...")
            return None
        return body

    def patch(
        self, pk: int, payload: Dict, lang: Optional[str] = None
    ) -> Optional[Tuple[int, Dict]]:
        """Update the given top-level fields, leaving every other field alone.

        Raises:
            MetadataFieldError: the payload touches ``linkedresources``

        Returns:
            Optional[Tuple[int, Dict]]: the status - 200, or 422 with the
                rejected fields in ``extraErrors``, or 404 - and the body
        """
        self.__guard_linked_resources__(payload)
        return self.http_patch(
            f"{self.ENDPOINT_NAME}/instance/{pk}",
            json_content=payload,
            params=self.__params__(lang),
            accept=(UNPROCESSABLE, NOT_FOUND),
        )

    def lookup(self, path: str, query: Optional[str] = None) -> Optional[List[Dict]]:
        """Search the lookup table the schema declares for ``path``.

        Raises:
            MetadataFieldError: ``path`` is not in the schema, or has no lookup
        """
        schema = self.schema()
        if schema is None:
            return None
        url = lookup_url(resolve_property(schema, path))
        if url is None:
            raise MetadataFieldError(
                f"{path} has no lookup - these do: {', '.join(lookup_paths(schema))}"
            )
        # the schema gives a path absolute to the server, so it already carries
        # any prefix the GeoNode is mounted under
        r = self.http_get_download(
            urljoin(self.url, url), params={"q": query} if query else {}
        )
        if r is None:
            return None
        try:
            body = r.json()
        except ValueError as e:
            logging.error(f"{r.url} did not return valid JSON: {e}")
            return None
        if (body.get("pagination") or {}).get("more"):
            logging.info("there are more results, narrow the query to see them ...")
        # hierarchical keywords come back as plain strings
        return [
            item if isinstance(item, dict) else {"id": item, "label": item}
            for item in body.get("results", [])
        ]

    def validate(
        self, pk: int, lang: Optional[str] = None, validator=None
    ) -> Optional[List[Dict]]:
        """Check the stored metadata of a resource against the server's schema.

        Returns:
            Optional[List[Dict]]: the violations, empty when valid, or None when
                the metadata could not be fetched
        """
        instance = self.get(pk, lang)
        if instance is None:
            return None
        schema = self.schema(lang) or {}
        if validator is None:
            validator = build_validator(schema, self.schema_url)
        return collect_errors(validator, for_validation(schema, instance))

    def __guard_linked_resources__(self, payload: Dict):
        if self.LINKED_RESOURCES_FIELD in payload:
            raise MetadataFieldError(
                f"{self.LINKED_RESOURCES_FIELD} cannot be changed through the "
                "metadata api - use 'geonodectl linked-resources add/delete' ..."
            )

    # cmdline ------------------------------------------------------------------

    def cmd_schema(
        self, field: Optional[str] = None, lang: Optional[str] = None, **kwargs
    ) -> int:
        """show the fields of the schema, or a single field in detail"""
        try:
            schema = self.schema(lang)
            if schema is None:
                return EXIT_FAILED
            subschema = resolve_property(schema, field) if field else schema
        except GeonodeUsageError as e:
            logging.error(str(e))
            return EXIT_USAGE

        if kwargs.get("json"):
            print_json(subschema)
        elif field:
            self.__print_field__(schema, field, subschema)
        else:
            self.__print_schema__(schema)
        return EXIT_OK

    def cmd_describe(
        self,
        pk: str,
        select: Optional[str] = None,
        lang: Optional[str] = None,
        **kwargs,
    ) -> int:
        """print the metadata of a resource as json"""
        try:
            _pk = self.__resolve_identifier__(pk)
        except GeonodeUsageError as e:
            logging.error(str(e))
            return EXIT_USAGE
        instance = self.get(_pk, lang)
        if instance is None:
            return EXIT_FAILED

        if select:
            keys = [key.strip() for key in select.split(",") if key.strip()]
            unknown = [key for key in keys if key not in instance]
            if unknown:
                hint = get_close_matches(unknown[0], list(instance), n=3)
                logging.error(
                    f"unknown metadata field {unknown[0]!r}"
                    + (f" - did you mean {', '.join(hint)}?" if hint else "")
                )
                return EXIT_USAGE
            instance = {key: instance[key] for key in keys}
        print_json(instance)
        return EXIT_OK

    def cmd_lookup(self, path: str, query: Optional[str] = None, **kwargs) -> int:
        """search the lookup table of a field for the ids it accepts"""
        try:
            results = self.lookup(path, query)
        except GeonodeUsageError as e:
            logging.error(str(e))
            return EXIT_USAGE
        if results is None:
            return EXIT_FAILED
        if kwargs.get("json"):
            print_json(results)
        else:
            show_list(
                headers=["id", "label"],
                values=[[item.get("id"), item.get("label")] for item in results],
            )
        return EXIT_OK

    def cmd_patch(
        self,
        pk: str,
        field_exprs: Optional[List[str]] = None,
        fields: Optional[str] = None,
        json_path: Optional[str] = None,
        dry_run: bool = False,
        no_validate: bool = False,
        lang: Optional[str] = None,
        **kwargs,
    ) -> int:
        """update some fields of one or more resources

        Every payload is prepared and checked before the first is sent, so a
        payload rejected here leaves every resource untouched.
        """
        try:
            pks = self.__parse_pk_string__(pk)
            ops = [parse_field_expr(expr) for expr in field_exprs or []]
            base = self.__load_payload__(fields, json_path)
            if not ops and not base:
                raise MetadataFieldError(
                    "nothing to change - give --field, --set or --json_path ..."
                )
            schema = self.schema(lang)
            if schema is None:
                return EXIT_FAILED
            payloads, exit_code = self.__prepare__(schema, pks, ops, base, lang)
            if not no_validate and not self.__payloads_valid__(schema, payloads):
                return EXIT_USAGE
        except (GeonodeUsageError, JsonSourceError, SchemaLoadError) as e:
            logging.error(str(e))
            return EXIT_USAGE

        if dry_run:
            print_json({str(_pk): payload for _pk, payload in payloads.items()})
            return exit_code

        results = [
            (_pk, self.patch(_pk, payload, lang)) for _pk, payload in payloads.items()
        ]
        return max(exit_code, self.__report__(results, **kwargs))

    def cmd_validate(self, pk: str, lang: Optional[str] = None, **kwargs) -> int:
        """check the stored metadata of resources against the server's schema"""
        try:
            pks = self.__parse_pk_string__(pk)
            schema = self.schema(lang)
            if schema is None:
                return EXIT_FAILED
            validator = build_validator(schema, self.schema_url)
        except (GeonodeUsageError, SchemaLoadError) as e:
            logging.error(str(e))
            return EXIT_USAGE

        report: List[Dict] = []
        unreachable = False
        for _pk in pks:
            errors = self.validate(_pk, lang, validator=validator)
            if errors is None:
                unreachable = True
                continue
            report.append({"pk": _pk, "valid": not errors, "errors": errors})

        if kwargs.get("json"):
            print_json(report)
        else:
            print_validation_report(report, noun="resource")
        if unreachable or not all(entry["valid"] for entry in report):
            return EXIT_FAILED
        return EXIT_OK

    # helpers ------------------------------------------------------------------

    @staticmethod
    def __load_payload__(fields: Optional[str], json_path: Optional[str]) -> Dict:
        """the json object given by --set or --json_path, {} when neither"""
        if not fields and not json_path:
            return {}
        payload = load_json_source(json_path=json_path, fields=fields)
        if not isinstance(payload, dict):
            raise MetadataFieldError("the metadata must be a json object ...")
        return payload

    def __prepare__(
        self,
        schema: Dict,
        pks: List[int],
        ops: List[FieldOp],
        base: Dict,
        lang: Optional[str],
    ) -> Tuple[Dict[int, Dict], int]:
        """the payload for every pk, and EXIT_FAILED if a pk could not be read"""
        payloads: Dict[int, Dict] = {}
        exit_code = EXIT_OK
        for _pk in pks:
            current = None
            if needs_current_instance(ops):
                current = self.get(_pk, lang)
                if current is None:
                    exit_code = EXIT_FAILED
                    continue
            payload = apply_ops(schema, ops, base, current)
            check_payload_keys(schema, payload)
            self.__guard_linked_resources__(payload)
            payloads[_pk] = payload
        return payloads, exit_code

    def __payloads_valid__(self, schema: Dict, payloads: Dict[int, Dict]) -> bool:
        """check each payload field against its property; report the failures"""
        report = []
        for _pk, payload in payloads.items():
            validator = build_validator(
                payload_schema(schema, payload), self.schema_url
            )
            errors = collect_errors(validator, for_validation(schema, payload))
            if errors:
                report.append({"pk": _pk, "valid": False, "errors": errors})
        if report:
            logging.error("the schema rejects the change, nothing was sent:")
            print_validation_report(report, noun="payload for resource")
        return not report

    def __report__(
        self, results: List[Tuple[int, Optional[Tuple[int, Dict]]]], **kwargs
    ) -> int:
        """print what the server said about each write, return the exit code"""
        exit_code = EXIT_OK
        records = []
        for _pk, result in results:
            if result is None:
                logging.error(f"updating the metadata of resource {_pk} failed ...")
                records.append({"pk": _pk, "status": None})
                exit_code = EXIT_FAILED
                continue
            status, body = result
            records.append({"pk": _pk, "status": status, **body})
            if status != 200:
                exit_code = EXIT_FAILED

        if kwargs.get("json"):
            print_json(records)
            return exit_code

        for record in records:
            if record["status"] is None:
                continue
            message = record.get("message", f"status {record['status']}")
            print(f"resource {record['pk']}: {message}")
            errors = flatten_errors(record.get("extraErrors") or {})
            if errors:
                show_list(headers=["path", "error"], values=[list(e) for e in errors])
        return exit_code

    def __print_schema__(self, schema: Dict):
        required = set(schema.get("required") or [])
        with_lookup = lookup_paths(schema)
        rows = []
        for name, subschema in (schema.get("properties") or {}).items():
            lookup = any(p == name or p.startswith(f"{name}.") for p in with_lookup)
            rows.append(
                [
                    name,
                    self.__type_name__(subschema),
                    "yes" if name in required else "",
                    "yes" if lookup else "",
                    subschema.get("title", ""),
                ]
            )
        show_list(headers=["field", "type", "required", "lookup", "title"], values=rows)

    def __print_field__(self, schema: Dict, field: str, subschema: Dict):
        nested = [
            p for p in lookup_paths(schema) if p == field or p.startswith(f"{field}.")
        ]
        show_list(
            headers=["key", "value"],
            values=[
                ["field", field],
                ["title", subschema.get("title", "")],
                ["type", self.__type_name__(subschema)],
                ["required", "yes" if field in (schema.get("required") or []) else ""],
                ["read-only", "yes" if subschema.get("readOnly") else ""],
                ["lookup", ", ".join(nested)],
                ["description", subschema.get("description", "")],
            ],
        )
        choices = choices_of(subschema)
        if choices:
            print()
            show_list(headers=["value", "title"], values=[list(c) for c in choices])

    @staticmethod
    def __type_name__(subschema: Dict) -> str:
        if is_reference(subschema):
            return "reference"
        items = subschema.get("items")
        if isinstance(items, dict):
            inner = "reference" if is_reference(items) else items.get("type", "object")
            return f"array<{inner}>"
        return "|".join(types_of(subschema)) or "object"
