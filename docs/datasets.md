# Datasets

Manage GeoNode datasets (vector layers, rasters, tabular data).

**Aliases:** `dataset`, `ds`

---

## List

```bash
geonodectl dataset list
geonodectl dataset list --search "soil"
geonodectl dataset list --filter owner.username=admin is_published=true
geonodectl dataset list --ordering title
geonodectl dataset list --page 2 --page-size 20
```

Options:

| Flag | Description |
|---|---|
| `--search TEXT` | Free-text search across title, abstract, keywords |
| `--filter KEY=VALUE …` | Filter by field (e.g. `owner.username=admin`) |
| `--ordering FIELD` | Sort field (default: `date_updated`). Prefix with `-` for descending |
| `--page N` | Page number (default: 1) |
| `--page-size N` | Results per page (default: 80) |

---

## Upload

```bash
# Upload a shapefile
geonodectl dataset upload -f /path/to/data.shp

# Upload and wait for processing to finish
geonodectl dataset upload -f /path/to/data.shp --wait

# Upload as a time series
geonodectl dataset upload -f /path/to/data.shp --time

# Overwrite an existing layer with the same name
geonodectl dataset upload -f /path/to/data.shp --overwrite-existing-layer
```

Options:

| Flag | Description |
|---|---|
| `-f`, `--file PATH` | Path to the file to upload (required) |
| `--wait` | Block until processing is finished and print the result |
| `--time` | Mark dataset as a time series |
| `--mosaic` | Declare upload as a raster mosaic |
| `--charset CHARSET` | File encoding (default: UTF-8) |
| `--overwrite-existing-layer` | Replace an existing layer with the same name |
| `--skip-existing-layer` | Skip upload if a layer with the same name already exists |

---

## Describe

```bash
# Single dataset
geonodectl dataset describe 36

# Multiple datasets
geonodectl dataset describe 1,2,3
geonodectl dataset describe 1-5
```

---

## Patch

```bash
# Patch using an inline JSON string
geonodectl dataset patch 36 --set '{"category": {"identifier": "biota"}}'

# Patch using a JSON file
geonodectl dataset patch 36 --json_path ./metadata.json

# Patch multiple datasets at once
geonodectl dataset patch 1-5 --set '{"is_published": true}'
```

The pk argument accepts a single pk, a comma-separated list (`1,2,3`), or a range (`1-5`).

---

## Delete

```bash
# Delete a single dataset
geonodectl dataset delete 36

# Delete multiple datasets
geonodectl dataset delete 1,2,3
geonodectl dataset delete 1-5
```
