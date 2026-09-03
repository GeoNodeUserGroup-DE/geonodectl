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
geonodectl documents upload -f /path/to/report.pdf --wait
```

Options:

| Flag | Description |
|---|---|
| `-f`, `--file PATH` | Path to the file to upload (required) |
| `--wait` | Block until processing is finished |

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
```

---

## Delete

```bash
geonodectl documents delete 12
geonodectl documents delete 10,11,12
```
