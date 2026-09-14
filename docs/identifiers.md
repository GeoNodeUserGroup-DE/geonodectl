# Identifiers: pk or uuid

Anywhere `geonodectl` names an object you can give either its **pk** or its **uuid**. The tool
works out which one it got.

```bash
geonodectl dataset describe 2162
geonodectl dataset describe 550e8400-e29b-41d4-a716-446655440000
```

A pk is a database id local to one GeoNode install. A uuid is stable and travels — it is what a
metadata harvest, a CSW record, a DOI landing page or a catalogue export carries — so a uuid is
usually the identifier you already have when you come from outside the instance.

---

## Where it works

Every argument that names a dataset, document, map, geoapp or resource:

```bash
# positional identifiers
geonodectl dataset patch <uuid> --set '{"title": "new title"}'
geonodectl documents delete <uuid>
geonodectl maps get-blob <uuid>
geonodectl attributes describe <uuid>
geonodectl resources metadata <uuid>
geonodectl dataset validate <uuid> --json_schema ./dataset-schema.json

# list arguments, element by element, and they can be mixed with pks
geonodectl maps maplayers add <map-uuid> <dataset-uuid> 42
geonodectl maps create --title "My Map" --maplayers <dataset-uuid> 36
geonodectl linked-resources add <uuid> --linked-to <other-uuid> 7
```

### Users and groups are pk-only

Users and groups are not GeoNode resources and have no uuid at all, so those commands keep
taking a pk:

```console
$ geonodectl users delete 550e8400-e29b-41d4-a716-446655440000
ERROR:root:GeonodeUsersHandler objects are identified by pk, not by uuid: 550e8400-...
$ echo $?
2
```

`users describe` and `groups describe` take their pk as an integer, so there argparse rejects a
uuid first, with its own usage message - also exit 2.

---

## A uuid goes on its own

Ranges (`1-5`) and lists (`1,2,3`) stay integer-only. A uuid is given as a single value:

```console
$ geonodectl dataset describe <uuid>,<uuid>
ERROR:root:Invalid pk ... not an integer ... (a uuid must be given on its own, not in a list)
$ echo $?
2
```

The list arguments above are the exception — `--maplayers`, `--linked-to`, `--resources` and
the positional datasets of `maps maplayers add`/`remove` take several identifiers, each of
which may be a pk or a uuid.

---

## The type is checked

A uuid names one specific object, so `geonodectl` refuses one that belongs to a different kind
of object than the command is about. This catches the copy-paste mistake rather than patching
the wrong thing:

```console
$ geonodectl dataset describe <uuid-of-a-map>
ERROR:root:uuid 6ba7b810-... is a map, not a dataset ...
$ echo $?
2
```

`resources` and `linked-resources` span every type, so they accept any resource uuid.

Geoapps are matched by exclusion: GeoNode reports a geoapp's own subtype — `geostory`,
`dashboard`, or whatever else a deployment registers — never the word `geoapp`, so
`geonodectl geoapps describe <uuid>` accepts any resource that is not a dataset, document or
map.

---

## Exit codes

The [shared contract](exit-codes.md) applies:

| Situation | Code |
|---|---|
| the uuid resolved and the command succeeded | `0` |
| no object has that uuid | `1` — a failed lookup, like a 404 on a pk |
| the uuid names the wrong kind of object | `2` — you asked for the wrong thing |
| the value is neither a pk nor a uuid | `2` |
| a uuid was given for a user or group | `2` |

---

## Cost

There is **no uuid route** in the GeoNode REST API — no viewset overrides `lookup_field`, so
every detail, patch and delete route is addressed by pk. A uuid is reachable only as a list
filter, which means `geonodectl` spends one extra request resolving it:

```
GET /api/v2/resources/?filter{uuid}=<uuid>&advertised=all
```

`uuid` is unique, so that returns at most one row, and the row carries `resource_type` — so
resolution and the type check together cost exactly one request. `advertised=all` is sent
because GeoNode's advertised filter applies to list queries but is skipped on a direct fetch;
without it a non-advertised resource would be invisible to a uuid lookup while
`GET /resources/<pk>` still returned it.

**A pk costs nothing** — it is used directly, with no lookup. In a loop over many objects,
prefer pks if you already have them:

```bash
# one extra request per iteration
for u in $(cat uuids.txt); do geonodectl dataset describe "$u"; done

# no extra requests
for pk in $(geonodectl --raw dataset list | jq -r '.[].pk'); do
    geonodectl dataset describe "$pk"
done
```

---

## Library use

`__resolve_identifier__` is available on every handler and returns a pk:

```python
from geonoderest.apiconf import GeonodeApiConf
from geonoderest.datasets import GeonodeDatasetsHandler
from geonoderest.exceptions import ResourceNotFoundError, UuidTypeMismatchError

handler = GeonodeDatasetsHandler(env=GeonodeApiConf.from_env_vars())

try:
    pk = handler.__resolve_identifier__("550e8400-e29b-41d4-a716-446655440000")
except UuidTypeMismatchError as e:
    print(f"wrong kind of object: {e}")
except ResourceNotFoundError as e:
    print(f"no such resource: {e}")
else:
    obj = handler.get(pk=pk)
```

Pass `expected=` to check against a type other than the handler's own — that is how
`maps maplayers add` validates its *dataset* arguments while the map itself is checked as a map.
As everywhere in `geonoderest`, these raise rather than exiting, so the library stays usable
inside a larger program.
