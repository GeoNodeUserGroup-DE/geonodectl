## How to use

geonodectl has the following capabilities:

| geonode resource | capabilities |
|------------------|--------------|
| resource         | list, delete, download metadata |
| dataset          | list, delete, patch, describe, upload |
| documents        | list, delete, patch, describe, upload |
| maps             | list, delete, patch, describe, create, get-blob, set-blob |
| geoapps          | list, delete, patch, describe |
| users            | list, delete, patch, describe, create, transfer_resources |
| groups           | list, delete, patch, describe, create |
| uploads          | list, describe |
| executionrequest | list, describe |
| keywords         | list, describe |
| tkeywords        | list, describe |
| tkeywordlabels   | list, describe |
| linked-resources | delete, add, describe |
| attributes       | describe, patch |
| geoserver styles | list, describe, upload, set-default |

This project is WIP, so feel free to add more capabilities.

---

### Dataset operations

Upload a shapefile:
```
❯ geonodectl ds upload -f ~/data/geolocation.shp -t example-shape
| key     | value                                       |
|---------|---------------------------------------------|
| title   | example-shape                               |
| success | True                                        |
| status  | finished                                    |
| bbox    | 13.1832819,52.4059715,13.5891838,52.5867805 |
| crs     | {'type': 'name', 'properties': 'EPSG:4326'} |
| url     | /catalogue/#/dataset/36                     |
```

List all datasets:
```
❯ geonodectl dataset list
|   pk | title         | owner.username | date                        | state     | detail_url                             |
|------|---------------|----------------|-----------------------------|-----------|----------------------------------------|
|   36 | example-shape | admin          | 2023-02-06T14:52:31.991113Z | PROCESSED | https://geonode.example.com/...        |
```

Patch a dataset:
```bash
geonodectl ds patch 36 --set '{"category":{"identifier":"biota"}}'
```

Patch from a JSON file:
```bash
geonodectl ds patch 36 --json_path path_to/attributes.json
```

Delete a dataset:
```
❯ geonodectl ds delete 36
deleted ...
```

Inside the `json-examples` folder you can find examples for patching datasets.

---

### Map blob operations

The MapStore blob is the JSON configuration that controls how a map is rendered in the GeoNode viewer (layers, zoom, center, widgets, featureInfo templates, etc.).

Fetch and inspect the blob:
```bash
# Print the full blob
geonodectl maps get-blob 2073

# Extract specific fields with jq
geonodectl maps get-blob 2073 | jq '.map.layers[].name'
geonodectl maps get-blob 2073 | jq '.map.center'
```

Replace the blob from a file:
```bash
geonodectl maps set-blob 2073 --json_path ./my_blob.json
```

A typical workflow for editing a blob:
```bash
# 1. Download the current blob
geonodectl maps get-blob 2073 > blob.json

# 2. Edit blob.json (update styles, zoom, layers, etc.)

# 3. Push it back
geonodectl maps set-blob 2073 --json_path blob.json
```

---

### GeoServer style management

The `geoserver` subcommand group requires GeoServer credentials:
```bash
export GEOSERVER_API_BASIC_AUTH=$(echo -n admin:password | base64)
# GEOSERVER_URL defaults to <GEONODE_API_URL base>/geoserver
```

List styles in a workspace:
```bash
geonodectl geoserver styles list --workspace geonode
```

Show the SLD XML for a style:
```bash
geonodectl geoserver styles describe foss4g_buildings --workspace geonode
```

Upload a new or updated SLD file:
```bash
geonodectl geoserver styles upload \
  --name foss4g_buildings \
  --sld-path ./buildings.sld \
  --workspace geonode
```

Set the default style for a GeoServer layer:
```bash
geonodectl geoserver styles set-default \
  --layer geonode:buildings \
  --style foss4g_buildings
```

**Style naming convention:** always prefix style names with a project slug (e.g. `foss4g_buildings`, not `buildings`) to avoid conflicts with GeoNode's auto-generated default styles.

---

### User operations

Transfer all resources from one user to another:
```bash
geonodectl users transfer_resources --from-user alice --to-user bob
```
