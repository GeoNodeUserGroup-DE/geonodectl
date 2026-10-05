# Documents

Manage GeoNode documents (PDFs, images, spreadsheets, and other file attachments).

**Aliases:** `documents`, `doc`, `document`

---

## List

```bash
geonodectl documents list
geonodectl documents list --search "report"
geonodectl documents list --filter owner.username=admin
geonodectl documents list --ordering title
```

Options:

| Flag | Description |
|---|---|
| `--search TEXT` | Free-text search |
| `--filter KEY=VALUE …` | Filter by field |
| `--ordering FIELD` | Sort field (default: `date_updated`) |
| `--page N` / `--page-size N` | Pagination |

---

## Upload

```bash
geonodectl documents upload -f /path/to/report.pdf
geonodectl documents upload -f /path/to/report.pdf -t "Station overview 2026"
geonodectl documents upload -f /path/to/report.pdf --metadata-only
```

Options:

| Flag | Description |
|---|---|
| `-f`, `--file PATH` | Path to the file to upload (required) |
| `-t`, `--title TITLE` | Title of the document (default: the file name) |
| `--metadata-only` | Do not generate a landing page; the file stays downloadable through its link |

The upload is synchronous - unlike `datasets upload` it does not create an
execution request, so there is nothing to wait for and no `--wait` flag.

Which endpoint is used depends on the GeoNode version, and is picked from the
methods the API advertises rather than configured:

| GeoNode | Endpoint |
|---|---|
| 5.0.3 and newer | `POST /documents/upload` - GeoNode removed document creation from the REST API ([geonode#14224](https://github.com/GeoNode/geonode/pull/14224)) so that uploads pass its magic-byte file check |
| 4.x, 5.0.0 - 5.0.2 | `POST /api/v2/documents` |

`--metadata-only` is applied with a follow-up `PATCH` on the newer endpoint,
whose upload form has no such field. Note that GeoNode then hides the document
from `/api/v2/documents` entirely - `documents describe` and `documents patch`
answer 404 for it, while `resources list` still shows it.

---

## Describe

```bash
geonodectl documents describe 12
geonodectl documents describe 10-15
```

---

## Patch

```bash
geonodectl documents patch 12 --set '{"abstract": "Updated abstract"}'
geonodectl documents patch 12 --json_path ./metadata.json
geonodectl documents patch 12 --json_path https://example.org/metadata.json
```

---

## Delete

```bash
geonodectl documents delete 12
geonodectl documents delete 10,11,12
```

---

## Validate

Check the metadata against a JSON Schema. See [validate.md](validate.md) for schema
authoring, exit codes and shared-baseline `$ref` use.

```bash
geonodectl documents validate 2135 --json_schema ./common-baseline.json
```
