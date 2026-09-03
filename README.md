# geonodectl Documentation

## Overview

**geonodectl** is a command-line interface (CLI) tool for interacting with the [GeoNode](https://geonode.org/) REST API v2. It allows users to manage datasets, resources, documents, maps, users, and more from the command line, making it ideal for automation, scripting, and power users.

- Project Repository: [https://github.com/GeoNodeUserGroup-DE/geonodectl](https://github.com/GeoNodeUserGroup-DE/geonodectl)
- License: MIT

## Features

- List, describe, upload, patch, and delete datasets, documents, maps, and geoapps
- Manage users, groups, uploads, execution requests, keywords, and linked resources
- Read and write the MapStore blob JSON for maps (`get-blob`, `set-blob`)
- Manage GeoServer styles — list, describe, upload SLD, set default style
- Transfer resources between users
- Supports authentication and secure API access
- Supports pagination, filtering, and ordering

## Installation

### From PyPI (recommended)
```bash
pip install geonodectl
```

### From Source (latest development version)
```bash
pip install -e 'git+https://github.com/GeoNodeUserGroup-DE/geonodectl.git@main#egg=geonodectl'
```

### Development Setup
```bash
pip install .[test]
pre-commit install
```

## Configuration

### GeoNode API

Set the following environment variables to connect to your GeoNode instance:

```bash
export GEONODE_API_URL=https://your-geonode-instance/api/v2/
export GEONODE_API_BASIC_AUTH=<base64-user:password>
```

Generate the basic auth string with:
```bash
echo -n user:password | base64
```

### GeoServer (for `geoserver` subcommands)

GeoServer credentials are required only for the `geoserver` subcommand group.

**Authentication** (in order of precedence):
```bash
# Option 1 — preferred, same format as GEONODE_API_BASIC_AUTH:
export GEOSERVER_API_BASIC_AUTH=<base64-admin:password>

# Option 2 — explicit username and password:
export GEOSERVER_USER=admin
export GEOSERVER_PASSWORD=geoserver
```

**URL** — defaults to the GeoNode base URL with `/geoserver` appended, so no extra config is needed in standard GeoNode deployments. Override if needed:
```bash
export GEOSERVER_URL=https://your-geonode-instance/geoserver  # optional
```

**SSL** — follows `GEONODE_API_VERIFY` (default: `True`).

## Usage

Get help and see available commands:
```bash
geonodectl --help
```

See [docs/example.md](docs/example.md) for worked examples.

## Command Reference

### GeoNode API commands

| Command | Aliases | Capabilities |
|---|---|---|
| `resources` | `resource` | list, delete, metadata |
| `datasets` | `ds`, `dataset` | list, delete, patch, describe, upload |
| `documents` | `doc`, `document` | list, delete, patch, describe, upload |
| `maps` | — | list, delete, patch, describe, create, **get-blob**, **set-blob** |
| `geoapps` | `apps` | list, delete, patch, describe |
| `users` | `user` | list, delete, patch, describe, create, transfer_resources |
| `groups` | — | list, delete, patch, describe, create |
| `uploads` | — | list, describe |
| `executionrequest` | `execrequest` | list, describe |
| `keywords` | — | list, describe |
| `tkeywords` | `thesaurikeywords` | list, describe |
| `tkeywordlabels` | `thesaurikeywordlabels` | list, describe |
| `linked-resources` | `linkedresources` | delete, add, describe |
| `attributes` | `attr`, `attribute` | describe, patch |

### GeoServer commands

The `geoserver` command group requires GeoServer credentials (see [Configuration](#geoserver-for-geoserver-subcommands) above).

| Command | Description |
|---|---|
| `geoserver styles list` | List styles in GeoServer, optionally filtered by workspace |
| `geoserver styles describe` | Print the SLD XML for a named style |
| `geoserver styles upload` | Create or update a style from an SLD file |
| `geoserver styles set-default` | Set the default style for a GeoServer layer |

#### Examples

```bash
# List all styles in the geonode workspace
geonodectl geoserver styles list --workspace geonode

# Show the SLD XML for a style
geonodectl geoserver styles describe foss4g_buildings --workspace geonode

# Upload a new or updated SLD file
geonodectl geoserver styles upload --name foss4g_buildings \
  --sld-path ./buildings.sld --workspace geonode

# Set the default style for a layer
geonodectl geoserver styles set-default \
  --layer geonode:buildings --style foss4g_buildings
```

### Map blob commands

The MapStore blob is the JSON configuration that controls how a map is rendered in the GeoNode MapStore viewer (layers, zoom, center, widgets, etc.).

```bash
# Print the blob JSON for map 2073 (pipe-friendly)
geonodectl maps get-blob 2073
geonodectl maps get-blob 2073 | jq '.map.layers'

# Replace the blob JSON from a file
geonodectl maps set-blob 2073 --json_path ./my_blob.json
```

## Development

### Code Quality

This project uses pre-commit hooks and GitHub Actions for:
- Black (code formatting)
- mypy (type checking)
- flake8 (linting)

Run checks locally:
```bash
pre-commit run --all-files
```

Or individually:
```bash
black .
mypy src/ --ignore-missing-imports
flake8 src/
```

### Testing

Tests are in `tests/`. Run with:
```bash
pytest
```

## Contribution Guide

1. Fork the repository and create a feature branch.
2. Install development dependencies: `pip install .[test]`
3. Install pre-commit hooks: `pre-commit install`
4. Make your changes and ensure all checks pass.
5. Submit a pull request.

## License

This project is licensed under the MIT License.

## Further Reading
- [GeoNode REST API v2 Documentation](https://docs.geonode.org/en/master/devel/api/V2/index.html)
- [GeoNode Project](https://geonode.org/)
