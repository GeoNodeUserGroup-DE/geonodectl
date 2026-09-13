"""JSON Schema validation of GeoNode metadata objects.

Wraps the ``jsonschema`` library so the handlers only deal with plain dicts:
:func:`build_validator` turns a schema into a validator and :func:`collect_errors`
turns a failed validation into flat records ready for printing.

Nothing in here talks to GeoNode or exits the process — see
``GeonodeResourceHandler.cmd_validate`` for the command line side.
"""

import json
from pathlib import Path
from typing import Any, Callable, Dict, List
from urllib.parse import urlsplit
from urllib.request import url2pathname

from jsonschema.exceptions import (
    SchemaError,
    _WrappedReferencingError,
    best_match,
)
from jsonschema.validators import validator_for
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012
from referencing.exceptions import NoSuchResource, Unresolvable

from geonoderest.jsonsource import (
    JsonSourceError,
    fetch_json_url,
    is_http_url,
    load_json,
)

# schemas that omit "$schema" are treated as the newest draft
DEFAULT_SPEC = DRAFT202012


class SchemaLoadError(Exception):
    """Raised when the schema itself cannot be used — not when data is invalid."""


def load_schema(json_schema: str) -> Dict:
    """Read a JSON Schema from disk, or over http(s) when given a URL.

    Args:
        json_schema (str): path to the schema file, or a http(s) url serving it

    Raises:
        SchemaLoadError: schema missing, unreachable, unreadable or not valid JSON
    """
    try:
        return load_json(json_schema, what="schema")
    except JsonSourceError as e:
        # one vocabulary for every schema problem, so cmd_validate can report
        # them all the same way and exit 2
        raise SchemaLoadError(str(e))


def __retrieve_local__(uri: str) -> Resource:
    """Resolve a ``$ref`` to a schema file on disk.

    A shared baseline schema is normally kept in its own file and pulled in with
    ``{"$ref": "common.json"}``. ``referencing.Registry`` never retrieves
    anything by itself, so relative refs only work if it is handed a callback
    like this one.
    """
    # as_uri() percent-encodes, so decode before touching the filesystem or a
    # schema kept under a path with a space or umlaut can never resolve its refs
    path = Path(url2pathname(urlsplit(uri).path))
    try:
        contents = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, IsADirectoryError):
        # NoSuchResource/Registry take attrs-aliased kwargs that mypy cannot see
        raise NoSuchResource(ref=uri)  # type: ignore[call-arg]
    except (json.decoder.JSONDecodeError, UnicodeDecodeError) as e:
        raise SchemaLoadError(f"referenced schema is not readable: {path}: {e}")
    return Resource.from_contents(contents, default_specification=DEFAULT_SPEC)


def __retrieve_remote__(uri: str) -> Resource:
    """Resolve a ``$ref`` to a schema served over http(s)."""
    try:
        contents = fetch_json_url(uri, what="schema")
    except JsonSourceError as e:
        raise SchemaLoadError(f"referenced schema is not readable: {e}")
    return Resource.from_contents(contents, default_specification=DEFAULT_SPEC)


def __make_retriever__(allow_remote: bool) -> Callable[[str], Resource]:
    """Build the ``referencing`` retrieve callback for one validator.

    ``allow_remote`` says which world the root schema came from, and a ``$ref``
    may never leave it: a schema read from disk must not make the tool reach out
    to the network, and a schema fetched from a url must not be able to read the
    local filesystem - an absolute ``file://`` ref plus a ``const`` would
    otherwise print the contents of the named file in the validation report.

    Results are cached for the life of the validator. ``referencing.Registry`` is
    immutable, so a resource it retrieves during one ``iter_errors()`` never
    lands back in the validator's own registry - without this, validating a pk
    range would re-fetch the same ``common.json`` once per object.
    """
    cache: Dict[str, Resource] = {}

    def retrieve(uri: str) -> Resource:
        if uri not in cache:
            if allow_remote:
                if not is_http_url(uri):
                    raise NoSuchResource(ref=uri)  # type: ignore[call-arg]
                cache[uri] = __retrieve_remote__(uri)
            else:
                if not uri.startswith("file://"):
                    raise NoSuchResource(ref=uri)  # type: ignore[call-arg]
                cache[uri] = __retrieve_local__(uri)
        return cache[uri]

    return retrieve


def build_validator(schema: Dict, schema_path: str):
    """Build a validator for ``schema``, honouring ``$schema`` and relative ``$ref``.

    Args:
        schema (Dict): the parsed schema
        schema_path (str): where it was read from - a path or a http(s) url -
            used as the base for relative ``$ref``s

    Raises:
        SchemaLoadError: the schema is not a valid JSON Schema
    """
    cls = validator_for(schema)
    try:
        cls.check_schema(schema)
    except SchemaError as e:
        location = "/".join(str(p) for p in e.absolute_path) or "<root>"
        raise SchemaLoadError(f"invalid JSON Schema at {location}: {e.message}")

    is_url = is_http_url(schema_path)
    base_uri = schema_path if is_url else Path(schema_path).resolve().as_uri()
    registry = Registry(retrieve=__make_retriever__(is_url)).with_resource(  # type: ignore[call-arg]
        uri=base_uri,
        resource=Resource.from_contents(schema, default_specification=DEFAULT_SPEC),
    )
    # validate through a $ref to the schema's own URI, so relative refs inside it
    # resolve against the directory - or the URL - it was read from
    return cls(
        {"$ref": base_uri},
        registry=registry,
        format_checker=cls.FORMAT_CHECKER,
    )


def collect_errors(validator, instance: Any) -> List[Dict]:
    """Validate ``instance`` and return every violation as a flat record.

    Raises:
        SchemaLoadError: a ``$ref`` in the schema could not be resolved. Refs are
            resolved lazily, at validation time rather than when the validator is
            built, so this surfaces here and not in :func:`build_validator`.

    Returns:
        List[Dict]: one record per violation with ``path``, ``keyword``,
            ``message`` and ``schema_path``; empty when the instance is valid.
    """
    try:
        errors = sorted(validator.iter_errors(instance), key=lambda e: list(e.path))
    except (_WrappedReferencingError, Unresolvable) as e:
        # a missing sibling file, or a remote ref from a local schema which we
        # deliberately do not fetch: the schema is unusable, which is not the
        # same as invalid metadata
        raise SchemaLoadError(f"could not resolve a $ref in the schema: {e}")

    records: List[Dict] = []
    for error in errors:
        message = error.message
        # "is not valid under any of the given schemas" says nothing useful on
        # its own, so surface the most relevant sub-error alongside it
        if error.context:
            sub = best_match(error.context)
            if sub is not None:
                message = f"{message} (best match: {sub.message})"

        records.append(
            {
                "path": error.json_path,
                "keyword": error.validator,
                "message": message,
                "schema_path": "/".join(str(p) for p in error.absolute_schema_path),
            }
        )
    return records


def validate_instance(instance: Any, schema: Dict, schema_path: str) -> List[Dict]:
    """Convenience wrapper: build a validator and collect its errors."""
    return collect_errors(build_validator(schema, schema_path), instance)
