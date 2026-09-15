# Extensions

geonodectl only ships commands that work against a vanilla GeoNode. Features that only a
customised GeoNode offers live in separate extension packages. Once an extension is installed next
to geonodectl, its commands show up in `geonodectl --help` and its handlers are available in
library mode. Nothing has to be configured.

---

## Using extensions

```bash
pip install geonodectl-zalf
geonodectl extensions list
```

```
| name   | distribution    | version   | status   |
|--------|-----------------|-----------|----------|
| zalf   | geonodectl-zalf | 0.1.0     | loaded   |
```

An extension that cannot be loaded prints a warning and is skipped. Reasons include an import
error, a different extension API version, or an extension that raises. The built-in commands
always keep working, and `extensions list` shows why the extension was skipped.

---

## Writing an extension

An extension is an ordinary Python package that depends on geonodectl.

### 1. Register the entry point

```toml
# pyproject.toml of the extension
[project]
name = "geonodectl-example"
dependencies = ["geonodectl>=0.4,<0.5"]

[project.entry-points."geonodectl.extensions"]
example = "geonodectl_example:extension"
```

The entry point refers to a `GeonodectlExtension` instance. A class works too, geonodectl
instantiates it.

### 2. Describe what it adds

```python
# src/geonodectl_example/__init__.py
from typing import List

from geonoderest.cliutils import SubParsers
from geonoderest.datasets import GeonodeDatasetsHandler
from geonoderest.exitcodes import EXIT_FAILED, EXIT_OK
from geonoderest.extensions import CommandSpec, GeonodectlExtension, VerbSpec
from geonoderest.geonodeobject import GeonodeObjectHandler


class SoilProfilesHandler(GeonodeObjectHandler):
    # list, describe, patch and delete come with GeonodeObjectHandler
    ENDPOINT_NAME = JSON_OBJECT_NAME = "soilprofiles"
    SINGULAR_RESOURCE_NAME = "soilprofile"


def build_soilprofiles_parser(parser) -> SubParsers:
    subparsers = parser.add_subparsers(dest="subcommand", required=True)
    subparsers.add_parser("list", help="list soil profiles")
    describe = subparsers.add_parser("describe", help="get soil profile details")
    describe.add_argument(dest="pk", type=str, help="pk of soil profile(s) to describe")
    return subparsers


def export_dataset(handler: GeonodeDatasetsHandler, pk: int, **kwargs) -> int:
    dataset = handler.get(pk=pk)
    if dataset is None:
        return EXIT_FAILED
    print(dataset["title"])
    return EXIT_OK


class ExampleExtension(GeonodectlExtension):
    name = "example"

    def commands(self) -> List[CommandSpec]:
        # geonodectl soilprofiles list / geonodectl sp describe 3
        return [
            CommandSpec(
                name="soilprofiles",
                aliases=("sp",),
                help="soil profile commands",
                build_parser=build_soilprofiles_parser,
                handler_factory=SoilProfilesHandler,
            )
        ]

    def verbs(self) -> List[VerbSpec]:
        # geonodectl dataset export 42
        return [
            VerbSpec(
                command="dataset",
                name="export",
                help="print the title of a dataset",
                build_parser=lambda parser: parser.add_argument(dest="pk", type=int),
                func=export_dataset,
            )
        ]


extension = ExampleExtension()
```

### What an extension can hand out

| Method | Returns | Adds |
|---|---|---|
| `commands()` | `List[CommandSpec]` | new top-level commands, `geonodectl <command> <verb>` |
| `verbs()` | `List[VerbSpec]` | new verbs on existing commands, `geonodectl dataset <verb>` |
| `handler_overrides()` | `List[HandlerOverride]` | a subclass taking over the handler of an existing command |

All three are imported from `geonoderest.extensions`.

**`CommandSpec`** fields:
- `name`: the command name.
- `build_parser`: fills the command's parser and returns its subparser group.
- `handler_factory`: called with the `GeonodeApiConf`; usually the handler class.
- `aliases`: further names for the command.
- `help`: one line for `geonodectl --help`.
- `description`: text for `geonodectl <command> --help`.
- `requires_env`: defaults to `True`. Set it to `False` for commands that don't talk to GeoNode;
  they then receive `None` instead of a `GeonodeApiConf`.

**`VerbSpec`** fields:
- `command`: the command to extend, by name or alias.
- `name`: the verb name.
- `func`: called as `func(handler, **arguments)`, where `handler` is the extended command's handler.
- `build_parser`: optional; adds the verb's arguments to its parser.
- `aliases`, `help`: as for `CommandSpec`.

**`HandlerOverride`** fields:
- `command`: the command, by name or alias.
- `handler_class`: must be a subclass of the command's current handler class.

The command keeps its parser and verbs; only the object doing the work changes. `geonodectl-zalf`
uses this to add the `keyword` column to `tkeywords list`.

### Rules

- **Dispatch**:
  - `geonodectl <command> <verb>` calls `cmd_<verb>` on the handler, with dashes turned into
    underscores. Add the verbs with `dest="subcommand"`.
  - Every parsed argument, including the global `json`, `page` and `page_size`, is passed as a
    keyword argument, so accept `**kwargs`.
  - For a nested group like `geonodectl maps widgets add`, call
    `geonoderest.cliutils.route_subcommands(widgets_subparsers, "cmd_widgets_")`
    once all its verbs are added.
- **Exit codes**: return `EXIT_OK`, `EXIT_FAILED` or `EXIT_USAGE` from `geonoderest.exitcodes`.
  Returning `None` counts as success. Raise `GeonodeUsageError` for input that cannot work, see
  [exit-codes.md](exit-codes.md).
- **Names**:
  - Built-in commands and their aliases cannot be taken.
  - When two extensions claim the same name, the first one in alphabetical order of the entry point
    name keeps it.
  - A verb that already exists on a command is skipped.
  - Every clash is reported as a warning.
- **Overrides**: one override per command. A command built by a factory function rather than a
  class, such as `geoserver`, cannot be overridden.
- **Parser helpers**: `geonoderest.cliutils` provides `add_json_source_args`,
  `add_validate_parser`, `kwargs_append_action` and `AliasedSubParsersAction`, so extension
  commands can take arguments the same way built-in commands do.
- **Compatibility**: `GeonodectlExtension.api_version` must equal
  `geonoderest.extensions.EXTENSION_API_VERSION`. The version changes only when extensions have to
  be adapted. Pin geonodectl to a minor version range in the extension's dependencies.

---

## Library use

Handlers of an extension can be imported from its package directly, or looked up by command name:

```python
from geonoderest.apiconf import GeonodeApiConf
from geonoderest.extensions import get_handler, list_extensions

conf = GeonodeApiConf.from_env_vars()

soilprofiles = get_handler("soilprofiles", conf)   # or the alias "sp"
soilprofiles.list(page_size=20)

for ext in list_extensions():
    print(ext.name, ext.version, ext.error or "loaded")
```

`get_handler` also applies handler overrides. It raises `UnknownCommandError`, a
`GeonodeUsageError`, if neither geonodectl nor an installed extension provides the command.

---

## Developing an extension

Install the extension in editable mode, so its entry point gets registered, then check that it
loaded:

```bash
pip install -e .
geonodectl extensions list
geonodectl soilprofiles --help
```

In tests, drive `geonoderest.geonodectl.geonodectl()` with a patched `sys.argv`, the same way the
geonodectl test suite does, and patch the handler's `http_*` methods. Clear the cache between
tests with `geonoderest.extensions._loaded_extensions = None`, or call `load_extensions(reload=True)`.
