# geonodectl — Python Library Skill Reference

This document is intended for **AI agents and developers** who want to use geonodectl as a **Python library** inside their own projects to interact with the GeoNode REST API v2 programmatically.

## Installation

```bash
pip install geonodectl
```

Or from source:
```bash
pip install -e 'git+https://github.com/GeoNodeUserGroup-DE/geonodectl.git@main#egg=geonodectl'
```

**Requirements**: Python ≥ 3.10

---

## Quick Start — Using geonodectl as a Library

```python
from geonoderest.apiconf import GeonodeApiConf
from geonoderest.datasets import GeonodeDatasetsHandler
from geonoderest.documents import GeonodeDocumentsHandler
from geonoderest.maps import GeonodeMapsHandler
from geonoderest.users import GeonodeUsersHandler
from geonoderest.resources import GeonodeResourceHandler
from geonoderest.linkedresources import GeonodeLinkedResourcesHandler
from geonoderest.keywords import GeonodeKeywordsRequestHandler

# 1. Create configuration (credentials + endpoint)
conf = GeonodeApiConf(
    url="https://geonode.example.com/api/v2/",
    auth_basic="YWRtaW46YWRtaW4=",  # base64 of user:password
    verify=True,                      # SSL verification
)

# Or load from environment variables (GEONODE_API_URL, GEONODE_API_BASIC_AUTH):
conf = GeonodeApiConf.from_env_vars()

# 2. Instantiate a handler
datasets = GeonodeDatasetsHandler(env=conf)

# 3. Call API methods
all_datasets = datasets.list(page_size=50, page=1)
single = datasets.get(pk=42)
```

---

## Core Classes

### `GeonodeApiConf` — Configuration Dataclass

**Import**: `from geonoderest.apiconf import GeonodeApiConf`

```python
@dataclass
class GeonodeApiConf:
    url: str          # GeoNode API v2 URL, e.g. "https://example.com/api/v2/"
    auth_basic: str   # Base64-encoded "user:password"
    verify: bool      # SSL certificate verification
```

**Factory methods**:

| Method | Description |
|---|---|
| `GeonodeApiConf.from_env_vars()` | Reads `GEONODE_API_URL` and `GEONODE_API_BASIC_AUTH` from environment |
| `GeonodeApiConf.from_env_file(path)` | Reads from a `.env` file |

---

### `GeonodeRest` — Low-Level HTTP Base Class

**Import**: `from geonoderest.rest import GeonodeRest`

All handlers inherit from this class. It provides:

| Method | Signature | Returns |
|---|---|---|
| `http_get` | `(endpoint: str, params: Dict = {})` | `Optional[Dict]` |
| `http_post` | `(endpoint: str, json: Dict = {}, params: Dict = {}, data: Dict = {}, files: Optional[List] = None, content_length: Optional[int] = None)` | `Optional[Dict]` |
| `http_patch` | `(endpoint: str, json_content: Dict = {}, params: Dict = {})` | `Optional[Dict]` |
| `http_delete` | `(endpoint: str, json: Dict = {}, params: Dict = {})` | `Optional[Dict]` |
| `http_get_download` | `(url: str, params: Dict = {})` | `Optional[requests.Response]` |

All methods raise `GeoNodeRestException` on connection errors.

---

### `GeonodeObjectHandler` — Base Handler

**Import**: `from geonoderest.geonodeobject import GeonodeObjectHandler`

Provides common CRUD operations inherited by all resource handlers:

| Method | Signature | Description |
|---|---|---|
| `list(**kwargs)` | `-> Optional[Dict]` | List objects with pagination/filtering |
| `get(pk: int, **kwargs)` | `-> Optional[Dict]` | Get single object by primary key |
| `delete(pk: int, **kwargs)` | `-> Optional[Dict]` | Delete object by primary key |
| `patch(pk: int, json_content: Optional[Dict], **kwargs)` | `-> Optional[Dict]` | Patch (partial update) an object |

**Common kwargs** (passed through to all methods):

| Kwarg | Type | Description |
|---|---|---|
| `page_size` | `int` | Results per page (default: 100) |
| `page` | `int` | Page number (default: 1) |
| `filter` | `Dict[str, str]` | Filter by field, e.g. `{"is_published": "true"}` |
| `search` | `str` | Free-text search term |
| `ordering` | `str` | Sort field, e.g. `"title"`, `"-date"` |
| `json` | `bool` | Used by `cmd_*` methods for output format (ignore in library use) |

---

## Resource Handlers — API Reference

### `GeonodeDatasetsHandler`

**Import**: `from geonoderest.datasets import GeonodeDatasetsHandler`

```python
datasets = GeonodeDatasetsHandler(env=conf)
```

| Method | Signature | Returns | Description |
|---|---|---|---|
| `list(**kwargs)` | | `Optional[Dict]` | List all datasets |
| `get(pk: int, **kwargs)` | | `Optional[Dict]` | Get dataset details |
| `delete(pk: int, **kwargs)` | | `Optional[Dict]` | Delete a dataset |
| `patch(pk: int, json_content: Dict, **kwargs)` | | `Optional[Dict]` | Update dataset metadata |
| `upload(file_path: Path, charset: str = "UTF-8", time: bool = False, mosaic: bool = False, overwrite_existing_layer: bool = False, skip_existing_layers: bool = False, **kwargs)` | | `Dict` | Upload a file as a new dataset |

**Upload example**:

```python
from pathlib import Path
from geonoderest.datasets import GeonodeDatasetsHandler
from geonoderest.apiconf import GeonodeApiConf

conf = GeonodeApiConf.from_env_vars()
ds = GeonodeDatasetsHandler(env=conf)

# Upload a GeoTIFF
result = ds.upload(file_path=Path("/data/raster.tif"))
print(result["execution_id"])  # Track upload progress

# Upload a Shapefile (must have .dbf, .shx, .prj next to the .shp)
result = ds.upload(file_path=Path("/data/boundaries.shp"))

# Patch metadata
ds.patch(pk=42, json_content={"title": "New Title", "abstract": "Updated abstract"})
```

**Supported upload file types**:
- Shapefiles (`.shp` — requires `.dbf`, `.shx`, `.prj` alongside)
- ZIP archives (`.zip`)
- Any other single file (GeoTIFF, GeoJSON, CSV, etc.)

---

### `GeonodeDocumentsHandler`

**Import**: `from geonoderest.documents import GeonodeDocumentsHandler`

```python
docs = GeonodeDocumentsHandler(env=conf)
```

| Method | Signature | Returns | Description |
|---|---|---|---|
| `list(**kwargs)` | | `Optional[Dict]` | List all documents |
| `get(pk: int, **kwargs)` | | `Optional[Dict]` | Get document details |
| `delete(pk: int, **kwargs)` | | `Optional[Dict]` | Delete a document |
| `patch(pk: int, json_content: Dict, **kwargs)` | | `Optional[Dict]` | Update document metadata |
| `upload(file_path: Path, charset: str = "UTF-8", metadata_only: bool = False, **kwargs)` | | `Optional[Dict]` | Upload a document |

```python
docs = GeonodeDocumentsHandler(env=conf)
result = docs.upload(file_path=Path("/reports/analysis.pdf"))
```

---

### `GeonodeMapsHandler`

**Import**: `from geonoderest.maps import GeonodeMapsHandler`

```python
maps = GeonodeMapsHandler(env=conf)
```

| Method | Signature | Returns | Description |
|---|---|---|---|
| `list(**kwargs)` | | `Optional[Dict]` | List all maps |
| `get(pk: int, **kwargs)` | | `Optional[Dict]` | Get map details |
| `delete(pk: int, **kwargs)` | | `Optional[Dict]` | Delete a map |
| `patch(pk: int, json_content: Dict, **kwargs)` | | `Optional[Dict]` | Update map metadata |
| `create(title: str, json_content: Optional[Dict] = None, maplayers: List[int] = [], **kwargs)` | | `Dict` | Create a new map |

```python
maps = GeonodeMapsHandler(env=conf)
new_map = maps.create(title="My Map", maplayers=[12, 34, 56])
```

---

### `GeonodeResourceHandler`

**Import**: `from geonoderest.resources import GeonodeResourceHandler`

Generic handler for all resource types. Also provides metadata download:

| Method | Signature | Returns | Description |
|---|---|---|---|
| `list(**kwargs)` | | `Optional[Dict]` | List all resources (datasets, docs, maps) |
| `delete(pk: int, **kwargs)` | | `Optional[Dict]` | Delete any resource |
| `metadata(pk: int, metadata_type: str = "ISO", **kwargs)` | | `requests.Response` | Download metadata in a given format |

**Supported metadata types**: `"Atom"`, `"DIF"`, `"Dublin Core"`, `"FGDC"`, `"ISO"`

```python
resources = GeonodeResourceHandler(env=conf)
response = resources.metadata(pk=42, metadata_type="ISO")
xml_content = response.text
```

---

### `GeonodeUsersHandler`

**Import**: `from geonoderest.users import GeonodeUsersHandler`

```python
users = GeonodeUsersHandler(env=conf)
```

| Method | Signature | Returns | Description |
|---|---|---|---|
| `list(**kwargs)` | | `Optional[Dict]` | List all users |
| `get(pk: int, user_resources: bool = False, user_groups: bool = False, **kwargs)` | | `Dict` | Get user details, optionally with resources or groups |
| `delete(pk: int, **kwargs)` | | `Optional[Dict]` | Delete user |
| `patch(pk: int, json_content: Dict, **kwargs)` | | `Optional[Dict]` | Update user |
| `create(json_content: Dict, **kwargs)` | | `Dict` | Create user |

```python
users = GeonodeUsersHandler(env=conf)
user_info = users.get(pk=5, user_resources=True)
# user_info["resources"] contains list of resources accessible by this user
```

---

### `GeonodeLinkedResourcesHandler`

**Import**: `from geonoderest.linkedresources import GeonodeLinkedResourcesHandler`

```python
lr = GeonodeLinkedResourcesHandler(env=conf)
```

| Method | Signature | Returns | Description |
|---|---|---|---|
| `get(pk: int, **kwargs)` | | `Dict` | Get linked resources (linked_to + linked_by) |
| `add(pk: int, linked_to: List[int], **kwargs)` | | `Dict` | Link resources to a target |
| `delete(pk: int, linked_to: List[int], **kwargs)` | | `Dict` | Remove linked resources |

```python
lr = GeonodeLinkedResourcesHandler(env=conf)

# Get links
links = lr.get(pk=42)
# links["linked_to"] -> list of resources this resource points to
# links["linked_by"] -> list of resources pointing to this resource

# Add links
lr.add(pk=42, linked_to=[10, 11, 12])

# Remove links
lr.delete(pk=42, linked_to=[10])
```

---

### `GeonodeKeywordsRequestHandler`

**Import**: `from geonoderest.keywords import GeonodeKeywordsRequestHandler`

```python
kw = GeonodeKeywordsRequestHandler(env=conf)
keywords = kw.list(page_size=200)
single_kw = kw.get(pk=5)
```

---

### `GeonodeExecutionRequestHandler`

**Import**: `from geonoderest.executionrequest import GeonodeExecutionRequestHandler`

Used to track asynchronous operations (e.g. upload progress):

```python
from geonoderest.executionrequest import GeonodeExecutionRequestHandler

er = GeonodeExecutionRequestHandler(env=conf)
status = er.get(exec_id="some-uuid-here")
# status["status"] -> "finished" | "failed" | "running"
```

---

## Common Patterns

### Pagination

```python
datasets = GeonodeDatasetsHandler(env=conf)

# Page through all datasets
page = 1
while True:
    result = datasets.list(page=page, page_size=50)
    if not result:
        break
    for ds in result:
        print(ds["pk"], ds["title"])
    if len(result) < 50:
        break
    page += 1
```

### Filtering and Search

```python
# Filter by field values
datasets.list(filter={"is_published": "true", "owner.username": "admin"})

# Free-text search
datasets.list(search="temperature")

# Ordering
datasets.list(ordering="-date")  # descending by date
```

### Upload and Wait for Completion

```python
import time
from geonoderest.datasets import GeonodeDatasetsHandler
from geonoderest.executionrequest import GeonodeExecutionRequestHandler

ds = GeonodeDatasetsHandler(env=conf)
er = GeonodeExecutionRequestHandler(env=conf)

result = ds.upload(file_path=Path("/data/myfile.tif"))
exec_id = result["execution_id"]

# Poll until complete
while True:
    status = er.get(exec_id=str(exec_id))
    if status["status"] in ("finished", "failed"):
        break
    time.sleep(5)

if status["status"] == "finished":
    for resource in status.get("output_params", {}).get("resources", []):
        print(f"Created dataset PK: {resource['id']}")
```

### Bulk Delete

```python
datasets = GeonodeDatasetsHandler(env=conf)
for pk in [101, 102, 103]:
    datasets.delete(pk=pk)
```

### Patch with JSON File

```python
import json

with open("metadata.json") as f:
    metadata = json.load(f)

datasets.patch(pk=42, json_content=metadata)
```

---

## Exception Handling

```python
from geonoderest.exceptions import GeoNodeRestException

try:
    datasets.get(pk=9999)
except GeoNodeRestException as e:
    print(f"API error: {e}")
```

All HTTP methods return `None` on HTTP errors (4xx/5xx) and log the error. Connection-level failures raise `GeoNodeRestException`.

---

## Class Hierarchy Summary

```
GeonodeRest                          # HTTP methods (get/post/patch/delete)
├── GeonodeObjectHandler             # CRUD: list, get, delete, patch
│   ├── GeonodeResourceHandler       # + metadata download
│   │   ├── GeonodeDatasetsHandler   # + upload (shapefile, zip, single file)
│   │   ├── GeonodeDocumentsHandler  # + upload (any document)
│   │   └── GeonodeGeoappsHandler
│   ├── GeonodeMapsHandler           # + create (with maplayers)
│   ├── GeonodeUsersHandler          # + create, user_resources, user_groups
│   ├── GeonodeGroupsHandler
│   ├── GeonodeUploadsHandler
│   ├── GeonodeExecutionRequestHandler
│   ├── GeonodeKeywordsRequestHandler
│   ├── GeonodeThesauriKeywordsRequestHandler
│   └── GeonodeThesauriKeywordLabelsRequestHandler
└── GeonodeLinkedResourcesHandler    # add/delete/get linked resources
```

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `GEONODE_API_URL` | Yes | GeoNode REST API v2 endpoint, e.g. `https://geonode.example.com/api/v2/` |
| `GEONODE_API_BASIC_AUTH` | Yes | Base64 of `user:password` (`echo -n user:password \| base64`) |
| `GEONODE_API_VERIFY` | No | `"True"` (default) or `"False"` for SSL verification |

---

## Package Metadata

- **PyPI**: `pip install geonodectl`
- **Import package**: `geonoderest`
- **Python**: ≥ 3.10
- **Dependencies**: `requests`, `tabulate`
- **Repository**: https://github.com/GeoNodeUserGroup-DE/geonodectl
- **License**: MIT
