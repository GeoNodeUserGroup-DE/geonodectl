# Validate

Check resource metadata against a [JSON Schema](https://json-schema.org/).

Available on `resources`, `dataset`, `documents`, `maps` and `geoapps` — the schema is
applied to the object exactly as the API returns it, which is the same JSON you get from
`describe`.

---

## Usage

```bash
geonodectl dataset validate 2162 --json_schema ./dataset-schema.json

# several at once: range, list or single pk
geonodectl dataset validate 1-5     --json_schema ./dataset-schema.json
geonodectl dataset validate 1,2,3   --json_schema ./dataset-schema.json

# any resource type, using only the shared baseline
geonodectl resources validate 2162 --json_schema ./common-baseline.json

# the same flag takes a http(s) url, so the schema need not live on disk
geonodectl dataset validate 2162 --json_schema https://example.org/schemas/dataset-schema.json
```

| Flag | Description |
|---|---|
| `--json_schema` | JSON Schema to validate against, as a path or a http(s) url (required) |

Output is a table of violations per object:

```
dataset 2162: invalid, 3 violation(s)
| path                           | keyword | message                                                   |
|--------------------------------|---------|-----------------------------------------------------------|
| $.attribute_set[0].description | type    | None is not of type 'string'                              |
| $.attribution                  | type    | None is not of type 'string'                              |
| $.license.identifier           | not     | 'not_specified' should not be valid under {'const': ...}  |

1 checked, 0 valid, 1 invalid
```

Add the global `--raw` flag (before the command) for a machine-readable report:

```bash
geonodectl --raw dataset validate 2162 --json_schema ./dataset-schema.json
```

```json
[
  {
    "pk": 2162,
    "valid": false,
    "errors": [
      {
        "path": "$.license.identifier",
        "keyword": "not",
        "message": "'not_specified' should not be valid under {'const': 'not_specified'}",
        "schema_path": "then/properties/license/properties/identifier/not"
      }
    ]
  }
]
```

---

## Exit codes

`validate` is meant to be used as a CI gate, so it signals the outcome through its exit code.
It follows the contract every command shares — see [exit-codes.md](exit-codes.md):

| Code | Meaning |
|---|---|
| 0 | every requested object validated |
| 1 | at least one object violated the schema, or could not be fetched |
| 2 | validation could not be carried out — schema missing, unreachable, not JSON, or not a valid JSON Schema |

```bash
geonodectl dataset validate 1-100 --json_schema ./dataset-schema.json || echo "metadata incomplete"
```

---

## Writing schemas

Any valid JSON Schema works; the draft is taken from the `$schema` keyword and defaults to
2020-12. A few patterns that map onto GeoNode metadata:

### Required fields

```json
{ "type": "object", "required": ["title", "abstract", "owner"] }
```

### Value patterns

```json
{
  "properties": {
    "doi": { "type": ["string", "null"], "pattern": "^10\\.\\d{4,9}/[-._;()/:A-Za-z0-9]+$" }
  }
}
```

### Conditional rules

"If a resource has a DOI, it must have a real license":

```json
{
  "if":   { "required": ["doi"], "properties": { "doi": { "type": "string" } } },
  "then": {
    "required": ["license", "attribution"],
    "properties": {
      "license": {
        "required": ["identifier"],
        "properties": { "identifier": { "not": { "const": "not_specified" } } }
      }
    }
  }
}
```

> **Note:** the `if` tests `"type": "string"` rather than just presence. GeoNode always emits
> the `doi` key and sets it to `null` when unset, so `{"required": ["doi"]}` alone would match
> every object.

### Attribute table completeness (datasets)

A dataset's columns come back in `attribute_set`, so requiring every column to be described
is a plain array rule — no extra API call:

```json
{
  "properties": {
    "attribute_set": {
      "type": "array",
      "minItems": 1,
      "items": {
        "required": ["attribute", "description"],
        "properties": { "description": { "type": "string", "minLength": 1 } }
      }
    }
  }
}
```

### Maplayer references (maps)

A map's layers come back in `maplayers`, each with the dataset embedded:

```json
{
  "required": ["maplayers"],
  "properties": {
    "maplayers": {
      "type": "array",
      "minItems": 1,
      "items": { "required": ["dataset"], "properties": { "dataset": { "required": ["pk"] } } }
    }
  }
}
```

---

## Hosting schemas centrally

A whole schema set can be served over http(s) instead of copied to every machine that runs
`geonodectl` — a git forge raw url, an intranet web server, an object store. Keep the files
next to each other so the relative `$ref`s keep working:

```bash
# https://example.org/schemas/ serves dataset-schema.json and common-baseline.json
geonodectl dataset validate 1-100 --json_schema https://example.org/schemas/dataset-schema.json
```

`geonodectl` fetches the url anonymously — your GeoNode credentials are never sent to it — so
the schema has to be readable without authentication.

---

## Sharing a baseline across object types

Metadata common to every object type belongs in one file that the per-type schemas pull in
with a relative `$ref`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "allOf": [{ "$ref": "common-baseline.json" }],
  "properties": { "attribute_set": { "type": "array", "minItems": 1 } }
}
```

References are resolved relative to whatever you passed to `--json_schema`: the directory the
schema was read from, or the url it was fetched from.

> **Note:** a schema read from **disk** resolves local files only — remote `http(s)` references
> are not fetched, so a local schema stays usable offline and validation cannot be changed by a
> third party. A schema you already pointed at a url has been trusted, so its relative refs are
> fetched over http(s) against that url.

Worked examples are in [json-examples/schemas/](https://github.com/GeoNodeUserGroup-DE/geonodectl/tree/main/json-examples/schemas):
`common-baseline.json`, `dataset-schema.json` and `map-schema.json`.

---

## Library use

`validate()` neither prints nor exits, so it can be used from `geonoderest` directly:

```python
from geonoderest.apiconf import GeonodeApiConf
from geonoderest.datasets import GeonodeDatasetsHandler
from geonoderest.validate import build_validator, load_schema

conf = GeonodeApiConf.from_env_vars()
schema_path = "dataset-schema.json"
# schema_path may equally be "https://example.org/schemas/dataset-schema.json"
validator = build_validator(load_schema(schema_path), schema_path)

datasets = GeonodeDatasetsHandler(env=conf)
violations = datasets.validate(pk=2162, validator=validator)
if violations:
    for v in violations:
        print(v["path"], v["message"])
```
