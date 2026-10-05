# Metadata

Read and edit resource metadata through GeoNode 5's JSON-schema metadata API (`/api/v2/metadata`).

**Aliases:** `metadata`, `md`

**Requires GeoNode 5.** GeoNode 4 has no metadata API, so every subcommand fails there, exiting 1 with a hint. On GeoNode 4, use `<type> patch`.

Everything below is driven by the schema the server hands out. That schema differs between GeoNode instances — custom fields, thesauri — so `geonodectl metadata schema` is the place to start.

> This is not `resources metadata`, which *exports* metadata as ISO 19139, Dublin Core and the other standard formats. `metadata get` returns GeoNode's own JSON, ready to be edited and written back.

---

## Schema

```bash
geonodectl metadata schema                  # every field: type, required, lookup, title
geonodectl metadata schema language         # one field in detail, with its allowed values
geonodectl metadata schema tkeywords.AGROVOC
geonodectl --json metadata schema           # the raw JSON schema
```

The `lookup` column marks fields whose valid values can be searched with `metadata lookup`.

---

## Get

```bash
geonodectl metadata get 42
geonodectl metadata get <uuid> --fields title,abstract,license
geonodectl metadata get 42 > md.json
```

| Option | Description |
|---|---|
| `--fields a,b` | only these fields |
| `--lang xx` | language of labels, e.g. `en` or `de` (default: the server's) |

`get` takes a single pk or uuid: its output is a document meant to be saved and edited.

---

## Lookup

Fields like `category`, `license`, `regions`, `contacts.owner` and the thesaurus keywords take ids from a lookup table. `lookup` searches that table:

```bash
geonodectl metadata lookup license
geonodectl metadata lookup category
geonodectl metadata lookup tkeywords.AGROVOC soil
geonodectl metadata lookup contacts.owner kerkow
```

The lookup endpoint is read from the schema, so new thesauri and custom fields work without changes to geonodectl. For a field without a lookup, the error lists every field that has one.

---

## Patch

Change some fields of one or more resources. Every field you don't name is left alone.

```bash
geonodectl metadata patch 42 --field license=CC-BY --field category=biota
geonodectl metadata patch 42 --field language=English
geonodectl metadata patch 40-45 --field hkeywords+=soil
geonodectl metadata patch 42 --field tkeywords.AGROVOC=http://aims.fao.org/aos/agrovoc/c_89
geonodectl metadata patch 42 --set '{"title": "New title"}'
geonodectl metadata patch 42 --json_path changes.json --dry-run
```

| Option | Description |
|---|---|
| `--field EXPR` | a change, repeatable — see below |
| `--set JSON` | the fields to change as a JSON string |
| `--json_path PATH` | the fields to change from a JSON file or a http(s) URL |
| `--dry-run` | print what would be sent, per pk, and send nothing |
| `--no-validate` | skip the schema check; the server still rejects bad values |
| `--lang xx` | language of messages |

The pk can be a pk, a uuid, a range (`40-45`) or a list (`1,2,3`). `--set` and `--json_path` exclude each other. `--field` may be combined with either, and its changes are applied on top.

### `--field` expressions

| Expression | Meaning |
|---|---|
| `KEY=VALUE` | set a field; the value is converted to what the field expects (below) |
| `KEY:=JSON` | set a field to a raw JSON value, unconverted |
| `KEY+=VALUE` | add to a list field; comma-separate several values |
| `KEY-=VALUE` | remove from a list field |
| `a.b=VALUE` | a nested field, e.g. `tkeywords.AGROVOC` or `contacts.owner` |

How a `KEY=VALUE` value is converted depends on the field's schema:

| Field | Example | Sent as |
|---|---|---|
| text, date | `title=Soil moisture` | `"Soil moisture"` |
| text that may be empty | `edition=` | `null` |
| choice list | `language=English` or `language=eng` | `"eng"`, matched case-insensitively against the value or its title |
| reference | `license=CC-BY` | `{"id": "CC-BY"}` |
| list of references | `regions=96,97` | `[{"id": "96"}, {"id": "97"}]` |
| list of text | `hkeywords=soil,water` | `["soil", "water"]` |
| number, true/false | `count=3`, `reviewed=true` | `3`, `true` |

For anything more complex, such as `contacts.contact_roles`, use `KEY:=JSON`. A value that doesn't fit is an error that lists the allowed values. Use `metadata lookup` to find ids.

**Nested fields and list edits are safe.** The API replaces top-level fields as a whole: sending only `tkeywords.AGROVOC` would drop every other thesaurus. So for `a.b=…`, `+=` and `-=`, geonodectl reads the current metadata first and sends the complete top-level value.

### Checked before sending

Unless `--no-validate` is given, every change is checked against the schema before anything is sent:

- field names must exist — typos come with a suggestion;
- read-only fields like `uuid` cannot be changed;
- each value must fit its field.

All payloads are checked first. If one is rejected, nothing is sent for any pk.

### Links are not edited here

`linkedresources` cannot be changed through `metadata`. Use `linked-resources add/delete`, which adds or removes single links atomically and also works on GeoNode 4. The metadata API replaces the whole list of links instead, so editing one link that way would be a read-modify-write that races other edits.

---

## Put

Replace the metadata of a resource with a complete document, typically one that `get` produced:

```bash
geonodectl metadata get 42 > md.json
$EDITOR md.json
geonodectl metadata put 42 --json_path md.json
```

| Option | Description |
|---|---|
| `--set JSON` / `--json_path PATH` | the metadata (one of them is required) |
| `--dry-run`, `--no-validate`, `--lang xx` | as for `patch` |

`put` writes every field except `linkedresources` and the read-only `uuid`. Your links are never touched, even if the file contains them. It is checked against the full schema, required fields included.

---

## Validate

Check the stored metadata of resources against the server's schema:

```bash
geonodectl metadata validate 42
geonodectl metadata validate 40-45
geonodectl --json metadata validate 40-45
```

This reports what the schema requires but the resource lacks, e.g. a missing `category`. This differs from `<type> validate --json_schema`, which checks against a schema *you* supply — see [Validate](validate.md).

GeoNode stores unset optional fields as `null` and some choice values in a different case than its schema lists them. Neither is reported as a violation: both are how GeoNode encodes data, and it accepts them back.

---

## Exit codes

| Code | When |
|---|---|
| `0` | success |
| `1` | the server rejected a change (its errors are shown as a table), a resource was not found, `validate` found invalid metadata, or the GeoNode has no metadata API |
| `2` | bad pk, unreadable JSON, unknown field, a value that doesn't fit, a rejected `linkedresources` change, or a schema violation found before sending — **nothing was sent** |

See [Exit Codes](exit-codes.md).
