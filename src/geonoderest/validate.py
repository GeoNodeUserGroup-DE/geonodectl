"""JSON Schema validation of GeoNode metadata objects.

Wraps the ``jsonschema`` library so the handlers only deal with plain dicts:
:func:`build_validator` turns a schema into a validator and :func:`collect_errors`
turns a failed validation into flat records ready for printing.

Nothing in here talks to GeoNode or exits the process — see
``GeonodeResourceHandler.cmd_validate`` for the command line side.
"""

import json
from pathlib import Path
from typing import Any, Dict, List

from jsonschema.exceptions import SchemaError, best_match
from jsonschema.validators import validator_for
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012
from referencing.exceptions import NoSuchResource

# schemas that omit "$schema" are treated as the newest draft
DEFAULT_SPEC = DRAFT202012


class SchemaLoadError(Exception):
    """Raised when the schema itself cannot be used — not when data is invalid."""


def load_schema(json_schema: str) -> Dict:
    """Read a JSON Schema from disk.

    Args:
        json_schema (str): path to the schema file

    Raises:
        SchemaLoadError: file missing, unreadable or not valid JSON
    """
    path = Path(json_schema)
    try:
        with open(path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        raise SchemaLoadError(f"schema file not found: {path}")
    except IsADirectoryError:
        raise SchemaLoadError(f"schema path is a directory: {path}")
    except PermissionError:
        raise SchemaLoadError(f"schema file not readable: {path}")
    except json.decoder.JSONDecodeError as e:
        raise SchemaLoadError(f"schema file is not valid JSON: {path}: {e}")


def __retrieve_local__(uri: str) -> Resource:
    """Resolve a ``$ref`` to a schema file on disk.

    A shared baseline schema is normally kept in its own file and pulled in with
    ``{"$ref": "common.json"}``. ``referencing.Registry`` never retrieves
    anything by itself, so relative refs only work if it is handed a callback
    like this one. Remote ``http(s)`` refs are deliberately not fetched.
    """
    # NoSuchResource/Registry take attrs-aliased kwargs that mypy cannot see
    if not uri.startswith("file://"):
        raise NoSuchResource(ref=uri)  # type: ignore[call-arg]
    path = Path(uri.removeprefix("file://"))
    try:
        contents = json.loads(path.read_text())
    except (FileNotFoundError, IsADirectoryError):
        raise NoSuchResource(ref=uri)  # type: ignore[call-arg]
    except json.decoder.JSONDecodeError as e:
        raise SchemaLoadError(f"referenced schema is not valid JSON: {path}: {e}")
    return Resource.from_contents(contents, default_specification=DEFAULT_SPEC)


def build_validator(schema: Dict, schema_path: str):
    """Build a validator for ``schema``, honouring ``$schema`` and local ``$ref``.

    Args:
        schema (Dict): the parsed schema
        schema_path (str): where it was read from, used as the base for ``$ref``

    Raises:
        SchemaLoadError: the schema is not a valid JSON Schema
    """
    cls = validator_for(schema)
    try:
        cls.check_schema(schema)
    except SchemaError as e:
        location = "/".join(str(p) for p in e.absolute_path) or "<root>"
        raise SchemaLoadError(f"invalid JSON Schema at {location}: {e.message}")

    path = Path(schema_path).resolve()
    registry = Registry(retrieve=__retrieve_local__).with_resource(  # type: ignore[call-arg]
        uri=path.as_uri(),
        resource=Resource.from_contents(schema, default_specification=DEFAULT_SPEC),
    )
    # validate through a $ref to the schema's own file URI, so relative refs
    # inside it resolve against the directory it was read from
    return cls(
        {"$ref": path.as_uri()},
        registry=registry,
        format_checker=cls.FORMAT_CHECKER,
    )


def collect_errors(validator, instance: Any) -> List[Dict]:
    """Validate ``instance`` and return every violation as a flat record.

    Returns:
        List[Dict]: one record per violation with ``path``, ``keyword``,
            ``message`` and ``schema_path``; empty when the instance is valid.
    """
    errors = sorted(validator.iter_errors(instance), key=lambda e: list(e.path))

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
