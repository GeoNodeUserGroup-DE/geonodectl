# Maps

Manage GeoNode maps, including reading and writing the MapStore blob JSON.

---

## List

```bash
geonodectl maps list
geonodectl maps list --search "Hiroshima"
geonodectl maps list --filter owner.username=admin
geonodectl maps list --ordering title
```

---

## Create

```bash
# Create with a title
geonodectl maps create --title "My New Map"

# Create from a JSON file, given as a path or a http(s) url
geonodectl maps create --json_path ./map_metadata.json
geonodectl maps create --json_path https://example.org/map_metadata.json

# Create with maplayers (space-separated dataset PKs)
geonodectl maps create --title "My Map" --maplayers 36 42 55
```

---

## Describe

```bash
geonodectl maps describe 2073
```

---

## Patch

```bash
geonodectl maps patch 2073 --set '{"title": "Updated Title"}'
geonodectl maps patch 2073 --json_path ./metadata.json
geonodectl maps patch 2073 --json_path https://example.org/metadata.json
```

---

## Delete

```bash
geonodectl maps delete 2073
geonodectl maps delete 2073,2074,2075
```

---

## get-blob

Print the MapStore blob JSON for a map. The blob controls the viewer configuration: layers, zoom level, center, styles, featureInfo templates, and widgets.

```bash
# Print the full blob
geonodectl maps get-blob 2073

# Extract specific fields with jq
geonodectl maps get-blob 2073 | jq '.map.layers[].name'
geonodectl maps get-blob 2073 | jq '.map.center'
geonodectl maps get-blob 2073 | jq '.map.zoom'
```

> **Note:** GeoNode omits the blob from the default API response, and its writable `blob`
> field is write-only. The readable representation is `data`, so this command requests it
> explicitly via `?include[]=data`.

---

## set-blob

Replace the MapStore blob JSON for a map from a JSON file, given as a path or a http(s) url.

```bash
geonodectl maps set-blob 2073 --json_path ./blob.json
geonodectl maps set-blob 2073 --json_path https://example.org/blobs/blob.json
```

### Typical workflow

```bash
# 1. Download the current blob
geonodectl maps get-blob 2073 > blob.json

# 2. Edit blob.json — update styles, center, zoom, add widgets, etc.

# 3. Push it back
geonodectl maps set-blob 2073 --json_path blob.json
```

### Minimal blob structure

The blob JSON must contain both `map` and `maplayers` top-level keys:

```json
{
  "version": 2,
  "map": {
    "projection": "EPSG:3857",
    "units": "m",
    "center": {"x": 13.4, "y": 52.5, "crs": "EPSG:4326"},
    "zoom": 10,
    "maxExtent": [-20037508.34, -20037508.34, 20037508.34, 20037508.34],
    "layers": [
      {
        "id": "mapnik__0",
        "group": "background",
        "source": "osm",
        "name": "mapnik",
        "title": "Open Street Map",
        "type": "osm",
        "visibility": true
      }
    ],
    "groups": [{"id": "Default", "title": "Default", "expanded": true}]
  },
  "maplayers": [],
  "widgetsConfig": {"widgets": []},
  "mapInfoConfiguration": {}
}
```

---

## maplayers

Manage the datasets shown on an existing map. Layers are addressed by **dataset pk**, the
same way `maps create --maplayers` takes them.

### maplayers list

```bash
geonodectl maps maplayers list 2073

# --raw/--json is a global flag and has to come before the command
geonodectl --raw maps maplayers list 2073
```

```
|   dataset.pk | name              | current_style     |   order | visibility   |   opacity |
|--------------|-------------------|-------------------|---------|--------------|-----------|
|         2162 | geonode:buildings | geonode:buildings |       0 | True         |         1 |
|         2163 | geonode:pois      | geonode:pois      |       1 | True         |         1 |
```

### maplayers add

```bash
geonodectl maps maplayers add 2073 2162 2163
```

Datasets already on the map are skipped with a warning. If none of the given datasets is
new, the map is left untouched.

### maplayers remove

```bash
geonodectl maps maplayers remove 2073 2162
```

Background layers (OpenStreetMap, OpenTopoMap, Sentinel-2 cloudless, empty) are never
removed, and the order of the remaining layers is renumbered.

### Typical workflow

```bash
# 1. Create a map
geonodectl maps create --title "My Map"

# 2. Put datasets on it
geonodectl maps maplayers add 2073 2162 2163 2164

# 3. Check what ended up there
geonodectl maps maplayers list 2073

# 4. Drop one again
geonodectl maps maplayers remove 2073 2164
```

### How it works

A map stores its layers twice: as `maplayers` rows in the API, and as layer entries inside
the MapStore blob. The two are joined by `maplayer.extra_params.msId` == `blob.map.layers[].id`.
Updating only one side leaves the map broken in the MapStore viewer, so both commands
rewrite both sides in a single PATCH.

> **Note:** the maps API replaces the whole `maplayers` list on PATCH — every maplayer
> missing from the payload is deleted. These commands therefore read the current list,
> modify it, and send it back complete, preserving the `pk` of untouched layers.

---

## widgets

Manage the MapStore widgets of an existing map. Widgets live in the map's blob under
`widgetsConfig.widgets` and are addressed by their **widget id**.

Currently only the `textbox` widget type is supported.

### widgets list

```bash
geonodectl maps widgets list 2073

# --raw/--json is a global flag and has to come before the command
geonodectl --json maps widgets list 2073
```

```
| id                                   | widgetType   | title       |
|--------------------------------------|--------------|-------------|
| 3fa85f64-5717-4562-b3fc-2c963f66afa6 | text         | Description |
| 9c1f2d0e-1b44-4f1a-9f7e-0d2c4b6a8e10 | text         | Sources     |
```

### widgets add

```bash
geonodectl maps widgets add 2073 textbox --title "test" --text "this is an example textbox"
```

`--text` is passed through to MapStore as **HTML** — the viewer renders it with the same
rich-text editor used in the widget builder:

```bash
geonodectl maps widgets add 2073 textbox \
    --title "Sources" \
    --text "<p>Data: <a href='https://example.org'>example.org</a></p>"
```

A raw widget definition can be supplied instead, which overrides `--title` and `--text`:

```bash
geonodectl maps widgets add 2073 textbox --json-path ./widget.json
```

Missing `id`, `widgetType` and `dataGrid` are filled in automatically, so the file can be
as small as `{"title": "test", "text": "hello"}`.

> **Note:** there is no `--description`. MapStore does not render a description for text
> widgets — it explicitly excludes them from the description tool, because the text body
> already serves that purpose. The flag would write a key the viewer never shows.

### widgets describe

```bash
geonodectl maps widgets describe 2073 3fa85f64-5717-4562-b3fc-2c963f66afa6
```

Prints the raw widget JSON, which is convenient as a starting point for `--json-path`.

### widgets remove

```bash
geonodectl maps widgets remove 2073 3fa85f64-5717-4562-b3fc-2c963f66afa6
```

Removing an id that is not on the map leaves the map untouched and warns.

### Typical workflow

```bash
# 1. Add a textbox
geonodectl maps widgets add 2073 textbox --title "About" --text "<p>What this map shows</p>"

# 2. Find its id
geonodectl maps widgets list 2073

# 3. Inspect it
geonodectl maps widgets describe 2073 <widget-id>

# 4. Drop it again
geonodectl maps widgets remove 2073 <widget-id>
```

### How it works

Unlike `maplayers`, widgets exist only inside the blob — there is no parallel API-side
list. Each command reads the blob, changes `widgetsConfig.widgets`, and writes the whole
blob back in a single PATCH.

New widgets are stacked downwards: the `dataGrid.y` of a new widget is one below the
lowest existing widget, so an added textbox never lands on top of one that is already
there.

The first widget on a map starts at row `2` rather than row `0`, which keeps it clear of
the controls along the top of the map. Adjust `GeonodeMapsHandler.WIDGET_TOP_OFFSET` to
move that starting point.

---

## Validate

Check the metadata against a JSON Schema. See [validate.md](validate.md) for schema
authoring, exit codes and shared-baseline `$ref` use.

```bash
geonodectl maps validate 2165 --json_schema ./map-schema.json
```
