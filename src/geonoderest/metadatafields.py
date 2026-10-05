"""Schema-driven helpers for GeoNode 5's metadata api (#174).

Everything here is pure - no http - so the rules that turn a ``--field``
expression into a metadata payload can be tested without a server. The schema
is never hardcoded: it differs between GeoNode instances, so every rule reads
the property it applies to from the schema the server handed out.
"""

from copy import deepcopy
from dataclasses import dataclass
from difflib import get_close_matches
import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from geonoderest.exceptions import MetadataFieldError

#: the ``ui:options`` key under which a property names its lookup endpoint,
#: either as a url or as ``{"url": ..., "creatable": true}``
AUTOCOMPLETE_KEY = "geonode-ui:autocomplete"

#: steps into the items of an array in a dotted path, e.g.
#: ``contacts.contact_roles.[].users``
ARRAY_STEP = "[]"

SET, JSON, APPEND, REMOVE = "set", "json", "append", "remove"

#: the character in front of ``=`` that picks the operation
OPERATORS = {":": JSON, "+": APPEND, "-": REMOVE}


@dataclass(frozen=True)
class FieldOp:
    """One parsed ``--field`` expression."""

    path: Tuple[str, ...]
    op: str
    raw: str

    @property
    def name(self) -> str:
        return ".".join(self.path)


def parse_field_expr(expr: str) -> FieldOp:
    """``KEY=VALUE``, ``KEY:=JSON``, ``KEY+=VALUE`` or ``KEY-=VALUE``.

    ``KEY`` may be a dotted path into an object, e.g. ``tkeywords.AGROVOC``.
    """
    index = expr.find("=")
    if index < 1:
        raise MetadataFieldError(
            f"cannot parse --field {expr!r}, expected KEY=VALUE, KEY:=JSON, "
            "KEY+=VALUE or KEY-=VALUE ..."
        )
    key, raw = expr[:index], expr[index + 1 :]
    op = OPERATORS.get(key[-1], SET)
    if op != SET:
        key = key[:-1]
    path = tuple(key.split("."))
    if not key or not all(path) or ARRAY_STEP in path:
        raise MetadataFieldError(f"cannot parse --field {expr!r}, bad field name ...")
    return FieldOp(path=path, op=op, raw=raw)


def resolve_property(schema: Dict, path) -> Dict:
    """The subschema of the property a dotted path names.

    Args:
        schema (Dict): the metadata schema
        path: a dotted string or a sequence of steps; ``[]`` steps into the
            items of an array

    Raises:
        MetadataFieldError: the schema has no such property
    """
    steps = path.split(".") if isinstance(path, str) else list(path)
    node = schema
    for i, step in enumerate(steps):
        if step == ARRAY_STEP:
            items = node.get("items")
            if not isinstance(items, dict):
                raise MetadataFieldError(
                    f"{'.'.join(steps[:i]) or 'the schema'} is not an array ..."
                )
            node = items
            continue
        properties = node.get("properties") or {}
        if step not in properties:
            where = ".".join(steps[:i])
            hint = get_close_matches(step, list(properties), n=3)
            raise MetadataFieldError(
                f"unknown metadata field {'.'.join(steps[: i + 1])!r}"
                + (f" - did you mean {', '.join(hint)}?" if hint else "")
                + (f" ({where} has: {', '.join(properties)})" if where else "")
            )
        node = properties[step]
    return node


def lookup_url(subschema: Dict) -> Optional[str]:
    """The lookup endpoint a property declares, or None when it has none."""
    autocomplete = (subschema.get("ui:options") or {}).get(AUTOCOMPLETE_KEY)
    if isinstance(autocomplete, dict):
        autocomplete = autocomplete.get("url")
    return autocomplete if isinstance(autocomplete, str) and autocomplete else None


def lookup_paths(schema: Dict) -> List[str]:
    """Every dotted path in the schema that declares a lookup endpoint."""
    found: List[str] = []

    def walk(node: Dict, path: List[str]):
        if path and lookup_url(node):
            found.append(".".join(path))
        for name, child in (node.get("properties") or {}).items():
            walk(child, path + [name])
        if isinstance(node.get("items"), dict):
            walk(node["items"], path + [ARRAY_STEP])

    walk(schema, [])
    return found


def types_of(subschema: Dict) -> List[str]:
    """The json types a property allows, ``null`` included."""
    declared = subschema.get("type")
    if declared is None:
        return []
    return list(declared) if isinstance(declared, list) else [declared]


def is_reference(subschema: Dict) -> bool:
    """A ``{"id", "label"}`` object pointing at something on the server -
    a category, a license, a user, a thesaurus keyword."""
    properties = subschema.get("properties") or {}
    return (
        "object" in types_of(subschema)
        and "id" in properties
        and set(properties) <= {"id", "label"}
    )


def choices_of(subschema: Dict) -> List[Tuple[Any, Optional[str]]]:
    """``(const, title)`` of an enumeration declared as ``oneOf``."""
    return [
        (option["const"], option.get("title"))
        for option in subschema.get("oneOf") or []
        if isinstance(option, dict) and "const" in option
    ]


def __choice__(subschema: Dict, raw: str, name: str) -> Any:
    """``raw`` as one of the enumeration's consts, accepting the title too."""
    choices = choices_of(subschema)
    for const, _ in choices:
        if raw == str(const):
            return const
    wanted = raw.casefold()
    for const, title in choices:
        if wanted in (str(const).casefold(), (title or "").casefold()):
            return const
    shown = ", ".join(f"{c} ({t})" if t else str(c) for c, t in choices[:15])
    more = f", ... see 'geonodectl metadata schema {name}'" if len(choices) > 15 else ""
    raise MetadataFieldError(
        f"{raw!r} is not a valid value for {name} - one of: {shown}{more}"
    )


def coerce(subschema: Dict, raw: str, name: str = "field") -> Any:
    """Turn the text of a ``--field`` value into what the property expects.

    Raises:
        MetadataFieldError: the value does not fit, or the property is too
            complex to be written as text - use ``KEY:=JSON`` for those
    """
    types = types_of(subschema)
    if raw == "" and "null" in types:
        return None
    if choices_of(subschema):
        return __choice__(subschema, raw, name)

    main = next((t for t in types if t != "null"), None)
    if main == "string":
        return raw
    if main in ("integer", "number"):
        try:
            return int(raw) if main == "integer" else float(raw)
        except ValueError:
            raise MetadataFieldError(f"{name} expects a {main}, got {raw!r} ...")
    if main == "boolean":
        if raw.lower() in ("true", "false"):
            return raw.lower() == "true"
        raise MetadataFieldError(f"{name} expects true or false, got {raw!r} ...")
    if main == "object" and is_reference(subschema):
        return {"id": raw}
    if main == "array" and isinstance(subschema.get("items"), dict):
        items = subschema["items"]
        if items.get("type") in ("string", "integer", "number") or is_reference(items):
            values = [value.strip() for value in raw.split(",") if value.strip()]
            return [coerce(items, value, name) for value in values]
    raise MetadataFieldError(
        f"{name} cannot be written as text, give it as json: {name}:=<json> ..."
    )


def __same_item__(left: Any, right: Any) -> bool:
    """references are the same when their ids are, anything else by value"""
    if isinstance(left, dict) and isinstance(right, dict) and "id" in right:
        return str(left.get("id")) == str(right["id"])
    return left == right


def __apply__(schema: Dict, op: FieldOp, payload: Dict, current: Optional[Dict]):
    subschema = resolve_property(schema, op.path)
    if op.op == JSON:
        try:
            value = json.loads(op.raw)
        except ValueError as e:
            raise MetadataFieldError(f"{op.name}:= is not valid json: {e}")
    else:
        value = coerce(subschema, op.raw, op.name)

    top = op.path[0]
    if len(op.path) == 1 and op.op in (SET, JSON):
        payload[top] = value
        return

    # a nested path or an array edit changes part of a top-level value, and
    # the server replaces top-level values wholesale - so start from what is
    # already there
    if top not in payload:
        payload[top] = deepcopy((current or {}).get(top))
    if len(op.path) == 1:
        container, leaf = payload, top
    else:
        if payload[top] is None:
            payload[top] = {}
        container = payload[top]
        for step in op.path[1:-1]:
            if container.get(step) is None:
                container[step] = {}
            container = container[step]
        leaf = op.path[-1]

    if op.op in (SET, JSON):
        container[leaf] = value
        return

    if "array" not in types_of(subschema):
        raise MetadataFieldError(f"{op.name} is not a list, += and -= need one ...")
    existing = list(container.get(leaf) or [])
    if op.op == APPEND:
        for item in value:
            if not any(__same_item__(old, item) for old in existing):
                existing.append(item)
    else:
        for item in value:
            kept = [old for old in existing if not __same_item__(old, item)]
            if len(kept) == len(existing):
                logging.warning(f"{op.name}: {op.raw} is not set, nothing removed ...")
            existing = kept
    container[leaf] = existing


def needs_current_instance(ops: List[FieldOp]) -> bool:
    """whether applying ``ops`` needs the instance as it is on the server"""
    return any(len(op.path) > 1 or op.op in (APPEND, REMOVE) for op in ops)


def apply_ops(
    schema: Dict,
    ops: List[FieldOp],
    payload: Optional[Dict] = None,
    current: Optional[Dict] = None,
) -> Dict:
    """Apply ``--field`` expressions on top of a payload.

    Args:
        schema (Dict): the metadata schema
        ops (List[FieldOp]): the parsed expressions, applied in order
        payload (Optional[Dict]): what ``--set``/``--json_path`` gave, if anything
        current (Optional[Dict]): the instance as it is on the server, needed
            whenever :func:`needs_current_instance` says so

    Returns:
        Dict: a new payload of top-level keys, ready for a PATCH
    """
    result = deepcopy(payload) if payload else {}
    for op in ops:
        __apply__(schema, op, result, current)
    return result


def check_payload_keys(schema: Dict, payload: Dict):
    """Every key must be a property of the schema, and not a read-only one.

    Raises:
        MetadataFieldError: an unknown key - with a suggestion, since this is
            mostly a typo - or a read-only one
    """
    for key in payload:
        subschema = resolve_property(schema, [key])
        if subschema.get("readOnly"):
            raise MetadataFieldError(f"{key} is read-only and cannot be changed ...")


def payload_schema(schema: Dict, keys) -> Dict:
    """A schema for a partial payload holding ``keys``.

    A PATCH only carries some fields, and stored instances are not always valid
    to begin with, so ``required`` would reject good payloads. Each value is
    checked against its own property instead.
    """
    properties = schema.get("properties") or {}
    derived: Dict = {
        "type": "object",
        "properties": {key: properties[key] for key in keys if key in properties},
        "additionalProperties": False,
    }
    if "$schema" in schema:
        derived["$schema"] = schema["$schema"]
    return derived


def for_validation(schema: Dict, instance: Any) -> Any:
    """A copy of ``instance`` to validate, tolerant of how GeoNode encodes data.

    Only the copy that is validated is changed - what gets sent is left as the
    user gave it, so a ``get`` -> ``put`` round-trip stays faithful. Two things
    GeoNode hands out itself would otherwise be reported as violations:

    - ``null`` for an optional field nobody has set, even where the schema
      types it as a plain string - at the top level and inside nested objects
      alike. That means "absent", and an absent optional field is valid, so it
      is left out. A required field that is ``null`` stays in: that one is a
      real gap. Each level is judged by its own ``required``.
    - an enumeration value in another case than the schema's ``const``, e.g.
      ``date_type: "Creation"`` where the schema lists ``creation``. GeoNode
      writes and accepts these, so they are matched case-insensitively.
    """
    if isinstance(instance, dict):
        properties = schema.get("properties") or {}
        required = set(schema.get("required") or [])
        return {
            key: for_validation(properties.get(key) or {}, value)
            for key, value in instance.items()
            if value is not None or key in required
        }
    if isinstance(instance, list) and isinstance(schema.get("items"), dict):
        return [for_validation(schema["items"], item) for item in instance]
    if isinstance(instance, str):
        wanted = instance.casefold()
        for const, _ in choices_of(schema):
            if isinstance(const, str) and const.casefold() == wanted:
                return const
    return instance


def flatten_errors(errors: Dict, path: Tuple[str, ...] = ()) -> List[Tuple[str, str]]:
    """``(path, message)`` for every message in the server's ``extraErrors``,
    a nested dict whose leaves are ``{"__errors": [message, ...]}``."""
    flat: List[Tuple[str, str]] = []
    for key, value in (errors or {}).items():
        if key == "__errors":
            flat.extend((".".join(path) or "<root>", str(m)) for m in value or [])
        elif isinstance(value, dict):
            flat.extend(flatten_errors(value, path + (str(key),)))
    return flat
