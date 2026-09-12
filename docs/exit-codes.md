# Exit codes

Every `geonodectl` command reports its outcome through its exit code, so `$?` is enough to
branch on in a shell script or fail a CI job — no scraping of stderr required.

| Code | Meaning |
|---|---|
| `0` | success — everything the command was asked to do worked |
| `1` | the operation failed — object not found, the API rejected the request, metadata violated a schema |
| `2` | the command could not be carried out as asked — an unparseable pk, missing env vars, unreadable input JSON |

`argparse` already exits `2` for its own usage errors (unknown verb, missing required
argument), so code `2` covers "you asked for something impossible" consistently.

```bash
geonodectl dataset describe 2162 || echo "dataset 2162 is not there"

if ! geonodectl dataset validate 1-100 --json_schema ./dataset-schema.json; then
    echo "metadata incomplete"; exit 1
fi
```

---

## Ranges and lists

For a pk range or list, **one failure is enough** to report failure. The command still visits
every pk rather than stopping at the first problem, so one run tells you about every object:

```console
$ geonodectl dataset patch 1-5 --set '{"is_published": true}'
ERROR:root:patching 3 failed ...
ERROR:root:patching 4 failed ...
$ echo $?
1
```

Three of the five were patched. The non-zero exit means a CI gate will never accept a
partially applied batch as clean.

---

## "Nothing to do" is a usage error

Commands that take a list of things to act on treat an empty list as code `2`, not as a
successful no-op — in practice an empty list is almost always an unset shell variable:

```console
$ geonodectl linked-resources add 42 --linked-to $PKS   # PKS is empty
ERROR:root:no --linked-to pks given, nothing to add ...
$ echo $?
2
```

The same applies to `maps maplayers add/remove` with no datasets.

---

## Using geonoderest as a library

The exit code is decided in exactly one layer. Library methods — `get`, `patch`, `delete`,
`upload`, `create`, … — never call `sys.exit`; they return a value or raise. Only `cmd_*`
methods and the `geonodectl()` dispatcher turn an outcome into an exit code. That is what
makes `geonoderest` safe to import into a larger program, which is the point of
[issue #69](https://github.com/GeoNodeUserGroup-DE/geonodectl/issues/69).

```python
from geonoderest.apiconf import GeonodeApiConf
from geonoderest.datasets import GeonodeDatasetsHandler
from geonoderest.exceptions import InvalidPkError

handler = GeonodeDatasetsHandler(env=GeonodeApiConf.from_env_vars())

try:
    pks = handler.__parse_pk_string__("1-5")
except InvalidPkError as e:      # a ValueError subclass
    print(f"bad pk: {e}")        # your process, your decision
else:
    for pk in pks:
        obj = handler.get(pk=pk)
        if obj is None:          # None on failure, never an exit
            print(f"{pk} not found")
```

Relevant exceptions, all in `geonoderest.exceptions`:

| Exception | Raised when |
|---|---|
| `InvalidPkError` | a pk argument is not a single pk, a range or a list (subclasses `ValueError`) |
| `ApiConfError` | `GEONODE_API_URL` / `GEONODE_API_BASIC_AUTH` are not set |
| `GeoNodeRestException` | the GeoNode API is unreachable, or an async operation never completed |

The constants themselves live in `geonoderest.exitcodes` as `EXIT_OK`, `EXIT_FAILED` and
`EXIT_USAGE`.
