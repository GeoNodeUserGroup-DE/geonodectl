# geonodectl Documentation

**geonodectl** is a command-line interface for the [GeoNode](https://geonode.org/) REST API v2.

- Repository: [https://github.com/GeoNodeUserGroup-DE/geonodectl](https://github.com/GeoNodeUserGroup-DE/geonodectl)
- License: MIT

---

## Quick start

```bash
pip install geonodectl

export GEONODE_API_URL=https://your-geonode.example.com/api/v2/
export GEONODE_API_BASIC_AUTH=$(echo -n user:password | base64)

geonodectl dataset list
```

---

## Feature documentation

| Document | Commands covered |
|---|---|
| [datasets.md](datasets.md) | `dataset list/upload/describe/patch/delete` |
| [documents.md](documents.md) | `documents list/upload/describe/patch/delete` |
| [maps.md](maps.md) | `maps list/create/describe/patch/delete/get-blob/set-blob` |
| [geoapps.md](geoapps.md) | `geoapps list/describe/patch/delete` |
| [users.md](users.md) | `users list/create/describe/patch/delete/transfer_resources` |
| [groups.md](groups.md) | `groups list/create/describe/patch/delete` |
| [resources.md](resources.md) | `resources list/delete/metadata` |
| [uploads.md](uploads.md) | `uploads list/describe` |
| [executionrequest.md](executionrequest.md) | `executionrequest list/describe` |
| [keywords.md](keywords.md) | `keywords`, `tkeywords`, `tkeywordlabels` |
| [linked-resources.md](linked-resources.md) | `linked-resources describe/add/delete` |
| [attributes.md](attributes.md) | `attributes describe/patch` |
| [geoserver.md](geoserver.md) | `geoserver styles list/describe/upload/set-default` |

See [example.md](example.md) for worked end-to-end examples.

---

## Development

```bash
pip install .[test]
pre-commit install
pytest                          # run tests (tests/ directory)
pre-commit run --all-files      # black + mypy + flake8
```

## Further reading

- [GeoNode REST API v2 docs](https://docs.geonode.org/en/master/devel/api/V2/index.html)
