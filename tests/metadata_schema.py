"""A trimmed copy of the metadata schema GeoNode 5 serves, for the metadata tests.

Taken from a live instance and cut down to one property of every shape the
``--field`` rules distinguish, plus two made-up scalar fields (``count`` and
``reviewed``) for the number and boolean rules, which the real schema lacks.
"""

from typing import Any, Dict

SCHEMA: Dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "http://example.org/api/v2/metadata/schema",
    "type": "object",
    "required": ["title", "date_type", "category", "language"],
    "properties": {
        "uuid": {"type": "string", "readOnly": True, "maxLength": 36},
        "title": {"type": "string", "title": "Title", "maxLength": 255},
        "edition": {"type": ["string", "null"], "maxLength": 255},
        "date": {"type": "string", "format": "date-time"},
        "date_type": {
            "type": "string",
            "title": "date type",
            "oneOf": [
                {"const": "creation", "title": "Creation"},
                {"const": "publication", "title": "Publication"},
                {"const": "revision", "title": "Revision"},
            ],
        },
        "language": {
            "type": "string",
            "oneOf": [
                {"const": "eng", "title": "English"},
                {"const": "ger", "title": "German"},
            ],
        },
        "maintenance_frequency": {
            "type": "string",
            "oneOf": [
                {"const": "unknown", "title": "frequency of maintenance is unknown"}
            ],
        },
        "category": {
            "type": "object",
            "properties": {"id": {"type": "string"}, "label": {"type": "string"}},
            "required": ["id"],
            "ui:options": {
                "geonode-ui:autocomplete": "/api/v2/metadata/autocomplete/categories"
            },
        },
        "regions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"id": {"type": "string"}, "label": {"type": "string"}},
            },
            "ui:options": {
                "geonode-ui:autocomplete": "/api/v2/metadata/autocomplete/regions"
            },
        },
        "hkeywords": {
            "type": "array",
            "items": {"type": "string"},
            "ui:options": {
                "geonode-ui:autocomplete": {
                    "url": "/api/v2/metadata/autocomplete/hkeywords",
                    "creatable": True,
                }
            },
        },
        "tkeywords": {
            "type": "object",
            "properties": {
                "AGROVOC": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "label": {"type": "string"},
                        },
                    },
                    "ui:options": {
                        "geonode-ui:autocomplete": "/api/v2/metadata/autocomplete/thesaurus/2/keywords"
                    },
                },
                "GEMET": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "label": {"type": "string"},
                        },
                    },
                    "ui:options": {
                        "geonode-ui:autocomplete": "/api/v2/metadata/autocomplete/thesaurus/1/keywords"
                    },
                },
            },
        },
        "contacts": {
            "type": "object",
            "properties": {
                "owner": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "label": {"type": "string"},
                    },
                    "required": ["id"],
                    "ui:options": {
                        "geonode-ui:autocomplete": "/api/v2/metadata/autocomplete/users"
                    },
                },
                "contact_roles": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "role": {"type": "string"},
                            "users": {
                                "type": "array",
                                "items": {"type": "object"},
                                "ui:options": {
                                    "geonode-ui:autocomplete": "/api/v2/metadata/autocomplete/users"
                                },
                            },
                        },
                    },
                },
            },
        },
        "related_identifier": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["related_identifier"],
                "properties": {
                    "related_identifier": {"type": "string"},
                    "resource_type_general": {
                        "type": "string",
                        "oneOf": [{"const": "Dataset", "title": "Dataset"}],
                    },
                },
            },
        },
        "linkedresources": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"id": {"type": "string"}, "label": {"type": "string"}},
            },
            "ui:options": {
                "geonode-ui:autocomplete": "/api/v2/metadata/autocomplete/resources"
            },
        },
        "count": {"type": "integer"},
        "reviewed": {"type": "boolean"},
    },
}

#: an instance the way GeoNode hands it out - including its quirks: ``null``
#: for optional fields nobody set, and an enum value in another case than the
#: schema's ``const``
INSTANCE: Dict[str, Any] = {
    "uuid": "3f0c5b52-6d8e-4a8b-9f43-2a1d2f4b6c7e",
    "title": "a dataset",
    "edition": None,
    "date": "2026-01-01T00:00:00Z",
    "date_type": "Creation",
    "language": "eng",
    "maintenance_frequency": None,
    "category": {"id": "biota", "label": "Biota"},
    "regions": [{"id": "96", "label": "Germany"}],
    "hkeywords": ["soil", "crop modeling"],
    "tkeywords": {
        "AGROVOC": [
            {"id": "http://aims.fao.org/aos/agrovoc/c_89", "label": "acid soils"}
        ],
        "GEMET": [
            {
                "id": "http://www.eionet.europa.eu/gemet/concept/319",
                "label": "alkali soil",
            }
        ],
    },
    "contacts": {
        "owner": {"id": "1355", "label": "OpenResearchData"},
        "contact_roles": [{"role": "author", "users": [{"id": "1455"}]}],
    },
    "related_identifier": [
        {"related_identifier": "https://example.org", "resource_type_general": None}
    ],
    "linkedresources": [{"id": "2087", "label": "soil cores"}],
}
