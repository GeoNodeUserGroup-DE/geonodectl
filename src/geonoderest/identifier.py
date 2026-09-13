"""Telling a ``pk`` and a ``uuid`` apart, and checking a uuid's object type.

A ``pk`` is an install-local database id, so anything that travels between
systems - a metadata harvest, a CSW record, a DOI landing page - carries the
resource ``uuid`` instead. Commands accept either (#160), which means deciding
which one was given and, for a uuid, checking it names the kind of object the
command is about.

Nothing in here talks to GeoNode - see ``GeonodeRest.__resolve_identifier__``
for the lookup that turns a uuid into a pk.
"""

import uuid as uuid_module

#: ``UUID_RESOURCE_TYPE`` for handlers whose verbs span every resource type,
#: i.e. ``resources`` and ``linked-resources``: any type resolves.
ANY_RESOURCE_TYPE = "*"

#: The resource types GeoNode reports under their own name. Everything else a
#: ``ResourceBase`` can be is a geoapp of some subtype - see
#: :func:`resource_type_matches`.
CORE_RESOURCE_TYPES = frozenset({"dataset", "document", "map"})


def is_uuid(value) -> bool:
    """True when ``value`` is a uuid rather than a pk.

    Strict on purpose: this is the switch that decides whether an argument is
    looked up as a uuid or used as a pk, so a near-miss must fall through to the
    pk path and be reported as a bad pk rather than sent to the API as a filter.
    """
    if not isinstance(value, str):
        return False
    try:
        uuid_module.UUID(value)
    except (ValueError, AttributeError, TypeError):
        return False
    return True


def canonical_uuid(value: str) -> str:
    """Return ``value`` in the lowercase dashed form GeoNode stores.

    ``uuid.UUID()`` also accepts uppercase, ``{braced}``, ``urn:uuid:`` and
    dashless spellings, and ``filter{uuid}`` is an exact string match - so a uuid
    pasted out of a catalogue export in any of those forms would match nothing
    unless it is normalised first.
    """
    return str(uuid_module.UUID(value))


def resource_type_matches(actual: str, expected: str) -> bool:
    """True when a resource of type ``actual`` satisfies a command about ``expected``.

    GeoNode never reports ``resource_type == "geoapp"``: a geoapp reports its own
    subtype - ``geostory``, ``dashboard``, or whatever else a deployment
    registers - so ``geoapp`` is matched by excluding the types that do report
    themselves by name.

    Args:
        actual (str): ``resource_type`` as returned by the API
        expected (str): the type the command is about, or :data:`ANY_RESOURCE_TYPE`
    """
    if expected == ANY_RESOURCE_TYPE:
        return True
    if not actual:
        # "geoapp" is an exclusion test, so an empty or missing resource_type
        # would otherwise satisfy it - refuse rather than guess
        return False
    if expected == "geoapp":
        return actual not in CORE_RESOURCE_TYPES
    return actual == expected


def describe_resource_type(expected: str) -> str:
    """Name ``expected`` the way an error message should, for the user."""
    if expected == ANY_RESOURCE_TYPE:
        return "resource"
    return expected
