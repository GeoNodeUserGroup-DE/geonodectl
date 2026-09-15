"""argparse building blocks shared by the geonodectl CLI and its extensions

Kept apart from ``geonodectl.py`` so an extension can build its parsers exactly
the way the core commands do without importing the CLI module itself (#133).
"""

import argparse
from typing import TypeAlias

# argparse defaults the dispatcher reads to find what a leaf parser runs. They
# are removed before the arguments reach a cmd_* method or an extension verb.
CMD_METHOD_KEY = "_cmd_method"
VERB_FUNC_KEY = "_verb_func"

SubParsers: TypeAlias = argparse._SubParsersAction


def route_subcommands(subparsers: SubParsers, prefix: str) -> None:
    """dispatch every verb of a nested subparser group to ``<prefix><verb>``

    The dispatcher calls ``cmd_<subcommand>`` by default. A group one level
    deeper, like ``maps widgets add``, names its method after the inner verb
    instead, so each of its leaves records the method to call.

    Args:
        subparsers: the nested subparser group, already holding all its verbs
        prefix (str): method name prefix, e.g. ``cmd_widgets_``
    """
    seen = set()
    # choices maps aliases to the same parser, the canonical name comes first
    for name, leaf in subparsers.choices.items():
        if id(leaf) in seen:
            continue
        seen.add(id(leaf))
        leaf.set_defaults(**{CMD_METHOD_KEY: prefix + name.replace("-", "_")})


class AliasedSubParsersAction(argparse._SubParsersAction):
    class _AliasedPseudoAction(argparse.Action):
        def __init__(self, name, aliases, help):
            dest = name
            if aliases:
                dest += " (%s)" % ",".join(aliases)
            super(AliasedSubParsersAction._AliasedPseudoAction, self).__init__(
                option_strings=[], dest=dest, help=help
            )

    def add_parser(self, name, **kwargs):
        if "aliases" in kwargs:
            aliases = kwargs["aliases"]
            del kwargs["aliases"]
        else:
            aliases = []

        parser = super(AliasedSubParsersAction, self).add_parser(name, **kwargs)

        # Make the aliases work.
        for alias in aliases:
            self._name_parser_map[alias] = parser
        # Make the help text reflect them, first removing old help entry.
        if "help" in kwargs:
            help = kwargs.pop("help")
            self._choices_actions.pop()
            pseudo_action = self._AliasedPseudoAction(name, aliases, help)
            self._choices_actions.append(pseudo_action)

        return parser


class kwargs_append_action(argparse.Action):
    """
    argparse action to split an argument into KEY=VALUE form
    on the first = and append to a dictionary.
    """

    def __call__(self, parser, args, values, option_string=None):
        try:
            d = dict(map(lambda x: x.split("="), values))
        except ValueError as _:
            raise argparse.ArgumentError(
                self,
                f'Could not parse argument "{values}" as field_name1=new_value1 field_name2=new_value2 ... format',
            )
        setattr(args, self.dest, d)


def add_json_source_args(
    target, subject: str, note: str = "", dashed_alias: bool = False
):
    """add the ``--json_path`` argument to a parser or argument group

    The argument takes a local path or a http(s) url interchangeably, see #159.
    It is defined once here instead of being repeated at each of the dozen call
    sites, so the wording stays identical across every verb.

    Args:
        target: a parser or a mutually exclusive group to add the argument to
        subject (str): what the json holds, used in the help text
            (e.g. "the metadata", "the new blob")
        note (str): extra remark appended to the help text
        dashed_alias (bool): also accept the ``--json-path`` spelling, kept for
            the verbs that already published it
    """
    flags = ["--json-path", "--json_path"] if dashed_alias else ["--json_path"]
    suffix = f" ({note})" if note else ""
    target.add_argument(
        *flags,
        dest="json_path",
        type=str,
        default=None,
        help=f"read {subject} from a json file, given as a path or a http(s) url{suffix}",
    )


def add_validate_parser(subparsers, noun: str):
    """add a `validate` subcommand to a resource's subparsers

    The four resource types take an identical validate verb, so it is built once
    here instead of being copied per resource.

    Args:
        subparsers: the resource's subparser group
        noun (str): singular name of the resource, used in the help texts
    """
    validate = subparsers.add_parser(
        "validate", help=f"validate {noun} metadata against a JSON schema"
    )
    validate.add_argument(
        type=str,
        dest="pk",
        help=f"pk or uuid of {noun}(s) to validate (uuid, single '1', range '1-5', list '1,2,3') ...",
    )
    validate.add_argument(
        "--json_schema",
        dest="json_schema",
        type=str,
        required=True,
        help="JSON Schema to validate the metadata against, given as a path or a \
http(s) url, relative $refs inside it are resolved against it",
    )
    return validate
