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

> **Note:** GeoNode omits the blob from the default API response. This command requests it explicitly via `?include[]=blob`.

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
