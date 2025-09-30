# geonodectl Documentation

## Overview

**geonodectl** is a command-line interface (CLI) tool for interacting with the [GeoNode](https://geonode.org/) REST API v2. It allows users to manage datasets, resources, documents, maps, users, and more from the command line, making it ideal for automation, scripting, and power users.

- Project Repository: [https://github.com/GeoNodeUserGroup-DE/geonodectl](https://github.com/GeoNodeUserGroup-DE/geonodectl)
- License: MIT

## Features

- List, describe, upload, patch, and delete datasets
- Manage resources, documents, maps, geoapps, users, uploads, execution requests, and keywords
- Download metadata and manage linked resources
- Supports authentication and secure API access
- Supports pagination, filtering, and ordering
- Pre-commit hooks and CI for code quality (black, mypy, flake8)

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

Set the following environment variables to connect to your GeoNode instance:

```
GEONODE_API_URL=https://your-geonode-instance/api/v2/
GEONODE_API_BASIC_AUTH=<base64-user:password>
```

You can generate the basic auth string with:
```bash
echo -n user:password | base64
```

## Usage

Get help and see available commands:
```bash
geonodectl --help
```

Example: List all datasets
```bash
geonodectl dataset list
```

Example: Upload a shapefile
```bash
geonodectl dataset upload -f /path/to/file.shp --title "My Dataset"
```

Example: Patch a dataset
```bash
geonodectl dataset patch 36 --set '{"category":{"identifier":"biota"}}'
```

## Command Reference

- `resources` / `resource`: List, delete, download metadata
- `dataset` / `ds`: List, delete, patch, describe, upload
- `documents` / `doc` / `document`: List, delete, patch, describe, upload
- `maps`: List, delete, patch, describe, create
- `geoapps` / `apps`: List, delete, patch, describe
- `users` / `user`: List, delete, patch, describe, create
- `uploads`: List, describe
- `executionrequest`: List, describe
- `keywords`: List, describe
- `tkeywords`: List, describe
- `tkeywordlabels`: List, describe

## Development

### Code Quality

This project uses pre-commit hooks and GitHub Actions for:
- Black (code formatting)
- mypy (type checking)
- flake8 (linting)

To run checks locally:
```bash
pre-commit run --all-files
```

### Testing

Tests are located in `src/geonoderest/tests/`.

Run tests with:
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
