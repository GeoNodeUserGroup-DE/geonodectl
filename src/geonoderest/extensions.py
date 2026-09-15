"""extension mechanism for geonodectl (#133)

geonodectl itself only talks to vanilla GeoNode. Whatever a single GeoNode
deployment adds on top lives in a separate package which, once installed, plugs
its commands into the ``geonodectl`` CLI and its handlers into library mode.

An extension package advertises itself through an entry point in its
pyproject.toml::

    [project.entry-points."geonodectl.extensions"]
    zalf = "geonodectl_zalf:extension"

The entry point refers to a :class:`GeonodectlExtension` (instance or class),
which hands out

* :class:`CommandSpec` - new top-level commands, ``geonodectl <command> <verb>``
* :class:`VerbSpec` - new verbs on existing commands, ``geonodectl dataset <verb>``
* :class:`HandlerOverride` - a subclass taking over an existing command's handler

A broken extension is reported and skipped, it never takes the core down.
"""

import argparse
import logging
from dataclasses import dataclass
from importlib.metadata import entry_points
from typing import Any, Callable, Dict, List, Optional, Tuple

from geonoderest.apiconf import GeonodeApiConf
from geonoderest.cliutils import CMD_METHOD_KEY, VERB_FUNC_KEY, SubParsers
from geonoderest.cmdprint import print_json, show_list
from geonoderest.exceptions import UnknownCommandError
from geonoderest.exitcodes import EXIT_OK

EXTENSION_API_VERSION = 1
ENTRY_POINT_GROUP = "geonodectl.extensions"
BUILTIN_ORIGIN = "geonodectl"

# called with the GeonodeApiConf, or None for commands not requiring the env.
# Typed loosely so plain handler classes, whose env is not Optional, fit.
HandlerFactory = Callable[..., Any]


@dataclass
class CommandSpec:
    """a top-level command, ``geonodectl <name> <verb> ...``

    Args:
        name (str): name of the command on the cmdline
        build_parser: fills the parser created for the command. It adds the
            verbs with ``dest="subcommand"`` and returns that subparser group,
            so extensions can add verbs to the command as well
        handler_factory: called with the GeonodeApiConf (None if
            ``requires_env`` is False), returns the handler - usually just the
            handler class. ``geonodectl <name> <verb>`` calls ``cmd_<verb>`` on it
        aliases (Tuple[str, ...]): further names of the command
        help (str): one line shown in ``geonodectl --help``
        description (str): shown in ``geonodectl <name> --help``
        requires_env (bool): the command needs GEONODE_API_URL and
            GEONODE_API_BASIC_AUTH to be set
    """

    name: str
    build_parser: Callable[[argparse.ArgumentParser], Optional[SubParsers]]
    handler_factory: HandlerFactory
    aliases: Tuple[str, ...] = ()
    help: str = ""
    description: Optional[str] = None
    requires_env: bool = True


@dataclass
class VerbSpec:
    """a verb added to an existing command, ``geonodectl <command> <name> ...``

    Args:
        command (str): name or alias of the command to extend
        name (str): name of the new verb
        func: called as ``func(handler, **arguments)`` with the handler of the
            extended command, returns an exit code (None counts as success)
        build_parser: adds the arguments of the verb to its parser
        aliases (Tuple[str, ...]): further names of the verb
        help (str): one line shown in ``geonodectl <command> --help``
    """

    command: str
    name: str
    func: Callable[..., Optional[int]]
    build_parser: Optional[Callable[[argparse.ArgumentParser], None]] = None
    aliases: Tuple[str, ...] = ()
    help: str = ""


@dataclass
class HandlerOverride:
    """let a subclass take over the handler of an existing command

    The command keeps its parser and verbs, only the object doing the work
    changes - e.g. to show columns a customised GeoNode backend returns.

    Args:
        command (str): name or alias of the command
        handler_class (type): subclass of the command's current handler class
    """

    command: str
    handler_class: type


class GeonodectlExtension:
    """base class for the object an extension's entry point refers to"""

    name: str = ""
    api_version: int = EXTENSION_API_VERSION

    def commands(self) -> List[CommandSpec]:
        return []

    def verbs(self) -> List[VerbSpec]:
        return []

    def handler_overrides(self) -> List[HandlerOverride]:
        return []


@dataclass
class LoadedExtension:
    """an installed extension, whether it could be loaded or not"""

    name: str
    distribution: str
    version: str
    extension: Optional[Any] = None
    error: Optional[str] = None


_loaded_extensions: Optional[List[LoadedExtension]] = None


def load_extensions(reload: bool = False) -> List[LoadedExtension]:
    """find and import every installed extension, once per process

    Args:
        reload (bool): search the entry points again instead of returning the
            cached result

    Returns:
        List[LoadedExtension]: installed extensions sorted by name, those that
            could not be loaded carry the reason in ``error``
    """
    global _loaded_extensions
    if _loaded_extensions is not None and not reload:
        return _loaded_extensions

    loaded = []
    for ep in sorted(entry_points(group=ENTRY_POINT_GROUP), key=lambda ep: ep.name):
        dist = getattr(ep, "dist", None)
        ext = LoadedExtension(
            name=ep.name,
            distribution=dist.name if dist is not None else "unknown",
            version=dist.version if dist is not None else "unknown",
        )
        try:
            obj = ep.load()
            if isinstance(obj, type):
                obj = obj()
        except Exception as e:  # an extension must never take the core down
            ext.error = f"could not be loaded: {e!r}"
        else:
            api_version = getattr(obj, "api_version", None)
            if api_version != EXTENSION_API_VERSION:
                ext.error = (
                    f"needs extension api version {api_version}, "
                    f"geonodectl provides {EXTENSION_API_VERSION}"
                )
            else:
                ext.extension = obj
        if ext.error is not None:
            logging.warning(f"geonodectl extension {ext.name} skipped, it {ext.error}")
        loaded.append(ext)

    _loaded_extensions = loaded
    return loaded


def _add_parser_or_rollback(
    subparsers: SubParsers,
    name: str,
    kwargs: Dict[str, Any],
    build: Callable[[argparse.ArgumentParser], Any],
) -> Any:
    """add a parser to a subparser group and fill it, or leave the group as it was

    Args:
        subparsers: subparser group to add the parser to
        name (str): name of the new parser
        kwargs (Dict): passed on to ``add_parser``
        build: fills the new parser, its return value is returned

    Raises:
        Exception: whatever ``build`` raised, after the parser was taken out again
    """
    choices_before = len(subparsers._choices_actions)
    names_before = dict(subparsers._name_parser_map)
    try:
        return build(subparsers.add_parser(name, **kwargs))
    except Exception:
        del subparsers._choices_actions[choices_before:]
        # the dict is shared with the action's choices, so change it in place
        subparsers._name_parser_map.clear()
        subparsers._name_parser_map.update(names_before)
        raise


@dataclass
class RegisteredCommand:
    """a command in the registry, together with where it came from"""

    spec: CommandSpec
    origin: str
    handler_factory: HandlerFactory
    overridden_by: Optional[str] = None
    subparsers: Optional[SubParsers] = None

    def run(self, env: Optional[GeonodeApiConf], arguments: Dict[str, Any]) -> Any:
        """build the handler and call what the parsed arguments point at

        Args:
            env (GeonodeApiConf): connection to GeoNode, None for commands that
                do not need one
            arguments (Dict): the parsed cmdline arguments

        Returns:
            the exit code returned by the called ``cmd_*`` method or verb
        """
        kwargs = dict(arguments)
        cmd_method = kwargs.pop(CMD_METHOD_KEY, None)
        verb_func = kwargs.pop(VERB_FUNC_KEY, None)

        handler = self.handler_factory(env)
        if verb_func is not None:
            return verb_func(handler, **kwargs)
        if cmd_method is None:
            subcommand = kwargs.get("subcommand")
            if subcommand is None:
                raise NotImplementedError(
                    f"command {self.spec.name} has no subcommand to dispatch to"
                )
            cmd_method = "cmd_" + subcommand.replace("-", "_")
        return getattr(handler, cmd_method)(**kwargs)


class CommandRegistry:
    """the commands geonodectl knows, built-ins first, then those of extensions

    The first command to claim a name keeps it, so an extension can never
    shadow a built-in command.
    """

    def __init__(self) -> None:
        self._commands: Dict[str, RegisteredCommand] = {}
        # every name and alias -> name of the command
        self._names: Dict[str, str] = {}
        self._verbs: List[Tuple[VerbSpec, str]] = []

    def __iter__(self):
        return iter(list(self._commands.values()))

    def resolve(self, name: str) -> Optional[RegisteredCommand]:
        """return the command going by a name or alias, None if there is none"""
        command_name = self._names.get(name)
        return None if command_name is None else self._commands[command_name]

    def add_command(self, spec: CommandSpec, origin: str = BUILTIN_ORIGIN) -> bool:
        """register a command, unless one of its names is taken already"""
        names = list(dict.fromkeys((spec.name, *spec.aliases)))
        taken = [name for name in names if name in self._names]
        if taken:
            owner = self._commands[self._names[taken[0]]].origin
            logging.warning(
                f"command {spec.name} of {origin} not added, "
                f"{', '.join(taken)} is already taken by {owner}"
            )
            return False
        self._commands[spec.name] = RegisteredCommand(
            spec=spec, origin=origin, handler_factory=spec.handler_factory
        )
        for name in names:
            self._names[name] = spec.name
        return True

    def add_verb(self, verb: VerbSpec, origin: str) -> None:
        """register a verb for an existing command, checked once parsers are built"""
        self._verbs.append((verb, origin))

    def override_handler(self, override: HandlerOverride, origin: str) -> bool:
        """let a subclass take over a command's handler, see HandlerOverride"""
        command = self.resolve(override.command)
        if command is None:
            logging.warning(
                f"handler override of {origin} ignored, "
                f"there is no command {override.command}"
            )
            return False
        if command.overridden_by is not None:
            logging.warning(
                f"handler override of {origin} for {command.spec.name} ignored, "
                f"it is already overridden by {command.overridden_by}"
            )
            return False
        base = command.spec.handler_factory
        if not (
            isinstance(base, type)
            and isinstance(override.handler_class, type)
            and issubclass(override.handler_class, base)
        ):
            logging.warning(
                f"handler override of {origin} for {command.spec.name} ignored, "
                f"{override.handler_class!r} is not a subclass of {base!r}"
            )
            return False
        command.handler_factory = override.handler_class
        command.overridden_by = origin
        return True

    def add_extension(self, loaded: LoadedExtension) -> None:
        """register the commands, verbs and handler overrides of an extension"""
        ext = loaded.extension
        if ext is None:
            return
        try:
            commands = list(getattr(ext, "commands", list)())
            verbs = list(getattr(ext, "verbs", list)())
            overrides = list(getattr(ext, "handler_overrides", list)())
        except Exception as e:  # an extension must never take the core down
            loaded.error = f"could not tell its commands: {e!r}"
            loaded.extension = None
            logging.warning(
                f"geonodectl extension {loaded.name} skipped, it {loaded.error}"
            )
            return

        for spec in commands:
            self.add_command(spec, origin=loaded.name)
        for verb in verbs:
            self.add_verb(verb, origin=loaded.name)
        for override in overrides:
            self.override_handler(override, origin=loaded.name)

    def _remove(self, command: RegisteredCommand) -> None:
        del self._commands[command.spec.name]
        self._names = {
            name: target
            for name, target in self._names.items()
            if target != command.spec.name
        }

    def build_parsers(self, subparsers: SubParsers) -> None:
        """add a parser for every command, then the verbs added to them

        Args:
            subparsers: the top-level subparser group of geonodectl
        """
        for command in self:
            spec = command.spec
            kwargs: Dict[str, Any] = {"help": spec.help}
            if spec.aliases:
                kwargs["aliases"] = spec.aliases
            if spec.description is not None:
                kwargs["description"] = spec.description

            if command.origin == BUILTIN_ORIGIN:
                command.subparsers = spec.build_parser(
                    subparsers.add_parser(spec.name, **kwargs)
                )
                continue
            try:
                command.subparsers = _add_parser_or_rollback(
                    subparsers, spec.name, kwargs, spec.build_parser
                )
            except Exception as e:  # an extension must never take the core down
                logging.warning(
                    f"command {spec.name} of {command.origin} skipped, "
                    f"building its parser failed: {e!r}"
                )
                self._remove(command)

        for verb, origin in self._verbs:
            self._add_verb_parser(verb, origin)

    def _add_verb_parser(self, verb: VerbSpec, origin: str) -> None:
        command = self.resolve(verb.command)
        if command is None or command.subparsers is None:
            logging.warning(
                f"verb {verb.name} of {origin} skipped, "
                f"there is no command {verb.command} taking verbs"
            )
            return
        subparsers = command.subparsers
        taken = [
            name
            for name in dict.fromkeys((verb.name, *verb.aliases))
            if name in subparsers.choices
        ]
        if taken:
            logging.warning(
                f"verb {verb.name} of {origin} skipped, "
                f"{command.spec.name} {', '.join(taken)} exists already"
            )
            return

        kwargs: Dict[str, Any] = {"help": verb.help}
        if verb.aliases:
            kwargs["aliases"] = verb.aliases

        def build(parser: argparse.ArgumentParser) -> None:
            if verb.build_parser is not None:
                verb.build_parser(parser)
            parser.set_defaults(**{VERB_FUNC_KEY: verb.func})

        try:
            _add_parser_or_rollback(subparsers, verb.name, kwargs, build)
        except Exception as e:  # an extension must never take the core down
            logging.warning(
                f"verb {verb.name} of {origin} skipped, "
                f"building its parser failed: {e!r}"
            )


def build_registry(builtins: Optional[List[CommandSpec]] = None) -> CommandRegistry:
    """register the built-in commands, then those of every installed extension

    Args:
        builtins (List[CommandSpec]): the built-in commands, taken from the
            geonodectl CLI if not given

    Returns:
        CommandRegistry: every command geonodectl can run
    """
    if builtins is None:
        # imported here, the CLI module itself imports this one
        from geonoderest.geonodectl import builtin_commands

        builtins = builtin_commands()

    registry = CommandRegistry()
    for spec in builtins:
        registry.add_command(spec)
    for loaded in load_extensions():
        registry.add_extension(loaded)
    return registry


def get_handler(command: str, env: Optional[GeonodeApiConf] = None) -> Any:
    """return the handler behind a built-in or extension command

    The library counterpart of ``geonodectl <command>``: aliases and handler
    overrides apply the same way, e.g. ``get_handler("tkeywordlabels", conf)``
    works once an extension providing that command is installed.

    Args:
        command (str): name or alias of the command
        env (GeonodeApiConf): connection to GeoNode

    Raises:
        UnknownCommandError: neither geonodectl nor an extension has the command
    """
    resolved = build_registry().resolve(command)
    if resolved is None:
        raise UnknownCommandError(f"unknown command: {command}")
    return resolved.handler_factory(env)


def list_extensions() -> List[LoadedExtension]:
    """return every installed extension, failed ones carry the reason in ``error``"""
    # registering them also reports extensions whose commands cannot be read
    build_registry()
    return load_extensions()


class GeonodeExtensionsHandler:
    """``geonodectl extensions``, works without a GeoNode connection"""

    def __init__(self, env: Optional[GeonodeApiConf] = None):
        self.gn_credentials = env

    def cmd_list(self, **kwargs) -> int:
        # the CLI has registered the extensions already, no need to do it again
        extensions = load_extensions()
        if kwargs.get("json"):
            print_json(
                {
                    "extensions": [
                        {
                            "name": ext.name,
                            "distribution": ext.distribution,
                            "version": ext.version,
                            "error": ext.error,
                        }
                        for ext in extensions
                    ]
                }
            )
        elif not extensions:
            print("no geonodectl extensions installed ...")
        else:
            show_list(
                headers=["name", "distribution", "version", "status"],
                values=[
                    [ext.name, ext.distribution, ext.version, ext.error or "loaded"]
                    for ext in extensions
                ],
            )
        return EXIT_OK
