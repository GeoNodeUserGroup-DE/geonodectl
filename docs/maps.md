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

# Create from a JSON file
geonodectl maps create --json_path ./map_metadata.json

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

Replace the MapStore blob JSON for a map from a JSON file.

```bash
geonodectl maps set-blob 2073 --json_path ./blob.json
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

## Validate

Check the metadata against a JSON Schema. See [validate.md](validate.md) for schema
authoring, exit codes and shared-baseline `$ref` use.

```bash
geonodectl maps validate 2165 --json_schema ./map-schema.json
```
