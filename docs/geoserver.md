# GeoServer Style Management

Manage SLD styles on the GeoServer instance associated with your GeoNode deployment.

> GeoNode's REST API does not support style uploads — these commands talk directly to the GeoServer REST admin API using separate credentials.

---

## Configuration

**Authentication** — set one of the following (in order of precedence):

```bash
# Preferred: Base64-encoded user:password (same format as GEONODE_API_BASIC_AUTH)
export GEOSERVER_API_BASIC_AUTH=$(echo -n admin:password | base64)

# Fallback: explicit username and password
export GEOSERVER_USER=admin
export GEOSERVER_PASSWORD=geoserver
```

**URL** — defaults to the GeoNode base URL with `/geoserver` appended, so no extra config is needed in standard GeoNode deployments:

```bash
# Optional — override only if GeoServer is at a non-standard path
export GEOSERVER_URL=https://your-geonode.example.com/geoserver
```

**SSL** — follows `GEONODE_API_VERIFY` (default: `True`).

---

## styles list

List styles available in GeoServer, optionally filtered to a workspace.

```bash
# List all styles in the geonode workspace
geonodectl geoserver styles list --workspace geonode

# List global (non-workspace) styles
geonodectl geoserver styles list
```

---

## styles describe

Print the raw SLD XML for a named style.

```bash
geonodectl geoserver styles describe foss4g_buildings --workspace geonode
geonodectl geoserver styles describe foss4g_buildings --workspace geonode > buildings.sld
```

---

## styles upload

Create a new style or update an existing one from a local SLD file.

```bash
geonodectl geoserver styles upload \
  --name foss4g_buildings \
  --sld-path ./buildings.sld \
  --workspace geonode
```

Options:

| Flag | Description |
|---|---|
| `--name NAME` | Style name in GeoServer (required) |
| `--sld-path PATH` | Path to the SLD 1.0 XML file (required) |
| `--workspace WS` | Target workspace (default: `geonode`) |

**Style naming convention:** always prefix style names with a project slug (e.g. `foss4g_buildings` rather than `buildings`). GeoNode auto-creates styles using bare layer names when datasets are uploaded — uploading to the same name causes a conflict.

If the style already exists, the command falls back to a direct PUT to update the SLD body.

---

## styles set-default

Set the default style for a GeoServer layer.

```bash
geonodectl geoserver styles set-default \
  --layer geonode:buildings \
  --style foss4g_buildings
```

The `--layer` argument accepts a fully qualified layer name (`workspace:name`) or a bare name, in which case `--workspace` is used as the layer workspace (default: `geonode`).

---

## Full workflow example

```bash
# 1. Check what styles already exist
geonodectl geoserver styles list --workspace geonode

# 2. Download the current style for inspection
geonodectl geoserver styles describe old_style --workspace geonode > old_style.sld

# 3. Write your new SLD and upload it
geonodectl geoserver styles upload \
  --name foss4g_buildings \
  --sld-path ./foss4g_buildings.sld \
  --workspace geonode

# 4. Set it as the default for the layer
geonodectl geoserver styles set-default \
  --layer geonode:buildings \
  --style foss4g_buildings
```
