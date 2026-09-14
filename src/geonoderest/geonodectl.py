#!/usr/bin/env python3

import logging
import os
import sys
import argparse
from typing import Optional, Union
from argparse import RawTextHelpFormatter
from pathlib import Path

from geonoderest.apiconf import GeonodeApiConf
from geonoderest.exceptions import GeoNodeRestException, GeonodeUsageError
from geonoderest.exitcodes import EXIT_FAILED, EXIT_OK, EXIT_USAGE
from geonoderest.geonodeobject import GeonodeObjectHandler
from geonoderest.datasets import GeonodeDatasetsHandler
from geonoderest.resources import (
    GeonodeResourceHandler,
    SUPPORTED_METADATA_TYPES,
    DEFAULT_METADATA_TYPE,
)
from geonoderest.documents import GeonodeDocumentsHandler
from geonoderest.maps import GeonodeMapsHandler
from geonoderest.users import GeonodeUsersHandler
from geonoderest.groups import GeonodeGroupsHandler
from geonoderest.geoapps import GeonodeGeoappsHandler
from geonoderest.uploads import GeonodeUploadsHandler
from geonoderest.executionrequest import GeonodeExecutionRequestHandler
from geonoderest.keywords import GeonodeKeywordsRequestHandler
from geonoderest.tkeywords import GeonodeThesauriKeywordsRequestHandler
from geonoderest.tkeywordlabels import GeonodeThesauriKeywordLabelsRequestHandler
from geonoderest.linkedresources import GeonodeLinkedResourcesHandler
from geonoderest.attributes import GeonodeAttributeHandler
from geonoderest.geoserver import (
    GeonodeGeoServerStyleHandler,
    GEOSERVER_URL_ENV_VAR,
    GEOSERVER_BASIC_AUTH_ENV_VAR,
    GEOSERVER_USER_ENV_VAR,
    GEOSERVER_PASSWORD_ENV_VAR,
    GEONODE_API_URL_ENV_VAR,
)

GEONODECTL_URL_ENV_VAR: str = "GEONODE_API_URL"
GEONODECTL_BASIC_ENV_VAR: str = "GEONODE_API_BASIC_AUTH"

DEFAULT_CHARSET: str = "UTF-8"
DEFAULT_CMD_PAGE_SIZE: int = 80
DEFAULT_CMD_PAGE: int = 1


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


# ---------------------------------------------------------------------------
# Argument helpers
#
# The same handful of arguments - an identifier, the list filters, --set - are
# taken by most verbs, and each used to be spelled out at every call site. That
# had grown to ~39 copies of the pk argument alone, with the wording drifting
# between them (#163). Each shape is defined once here; what genuinely differs
# per verb is passed in.
# ---------------------------------------------------------------------------

#: how an identifier argument that accepts a range or a list describes itself.
#: the uuid form is only offered for objects that actually have one (#160).
PK_RANGE_HINT = "single '1', range '1-5', list '1,2,3'"
PK_RANGE_HINT_UUID = f"uuid, {PK_RANGE_HINT}"


def add_pk_arg(
    target,
    noun: str,
    verb: Optional[str] = None,
    multiple: bool = False,
    uuid: bool = True,
    metavar: Optional[str] = None,
):
    """add the positional identifier argument a verb acts on

    Args:
        target: the parser to add the argument to
        noun (str): what is addressed, singular, e.g. "dataset", "map"
        verb (str): what is done to it, e.g. "describe", "fetch blob from".
            None when the verb is obvious from the command itself.
        multiple (bool): a range or comma list is accepted as well as one value
        uuid (bool): the object has a uuid, so either identifier is accepted.
            False for users and groups, which are not GeoNode resources (#160).
        metavar (str): override how the argument is shown in the usage line
    """
    kind = "pk or uuid" if uuid else "pk"
    subject = f"{noun}(s)" if multiple else noun
    if verb is None:
        text = f"{kind} of {subject} ..."
    elif multiple:
        hint = PK_RANGE_HINT_UUID if uuid else PK_RANGE_HINT
        text = f"{kind} of {subject} to {verb} ({hint}) ..."
    else:
        text = f"{kind} of {subject} to {verb}"
    kwargs = {"metavar": metavar} if metavar else {}
    target.add_argument(type=str if uuid else int, dest="pk", help=text, **kwargs)


def add_list_args(
    target,
    noun: str,
    ordering_default: str,
    search_example: str,
    filter_example: Optional[str] = None,
    ordering_example: str = "title",
):
    """add the ``--ordering``/``--search``/``--filter`` trio a list verb takes

    Args:
        target: the list parser to add the arguments to
        noun (str): plural name used in the help texts, e.g. "datasets"
        ordering_default (str): field the endpoint sorts by by default
        search_example (str): a plausible ``--search`` term for this noun
        filter_example (str): a plausible ``--filter`` expression; when omitted
            the verb gets no ``--filter`` at all
        ordering_example (str): a field worth ordering by, for the help text
    """
    target.add_argument(
        "--ordering",
        dest="ordering",
        default=ordering_default,
        type=str,
        help=f"Which field to use when ordering the results. "
        f"--ordering {ordering_example} (default: {ordering_default})",
    )
    target.add_argument(
        "--search",
        dest="search",
        type=str,
        required=False,
        help=f"A search term to filter the results by. --search {search_example}",
    )
    if filter_example is not None:
        target.add_argument(
            "--filter",
            nargs="*",
            action=kwargs_append_action,
            dest="filter",
            type=str,
            help=f"filter {noun} by key value pairs. E.g. --filter {filter_example}",
        )


def add_fields_arg(target, action: str, example: str, note: str = ""):
    """add the ``--set`` argument that takes an inline json string

    Args:
        target: a parser or a mutually exclusive group
        action (str): what the json does, e.g. "patch metadata"
        example (str): a json string showing the shape, without quotes
        note (str): extra remark appended to the help text
    """
    suffix = f" ... ({note})" if note else ""
    target.add_argument(
        "--set",
        dest="fields",
        type=str,
        help=f"{action} by providing a json string like: '{example}'{suffix}",
    )


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
    add_pk_arg(validate, noun, "validate", multiple=True)
    validate.add_argument(
        "--json_schema",
        dest="json_schema",
        type=str,
        required=True,
        help="JSON Schema to validate the metadata against, given as a path or a \
http(s) url, relative $refs inside it are resolved against it",
    )
    return validate


def __exit_code__(returned) -> int:
    """Normalise what a ``cmd_*`` method returned into an exit code.

    A ``cmd_*`` that has nothing to report returns ``None``, which is success -
    that keeps every not-yet-converted command working unchanged (#151).
    """
    return EXIT_OK if returned is None else int(returned)


def geonodectl() -> int:
    """Entry point: run the requested command and return its exit code.

    The one place allowed to exit the process, so every error the library raises
    has to be turned into a code here rather than escaping as a traceback (#151).
    """
    try:
        return __geonodectl__()
    except GeonodeUsageError as e:
        logging.error(str(e))
        return EXIT_USAGE
    except GeoNodeRestException as e:
        # the API is unreachable or refused the connection
        logging.error(str(e))
        return EXIT_FAILED
    except BrokenPipeError:
        # `geonodectl ... | head` closes the pipe early; not an error
        return EXIT_OK
    except KeyboardInterrupt:
        logging.error("interrupted ...")
        return EXIT_FAILED


def __geonodectl__() -> int:
    parser = argparse.ArgumentParser(
        prog="geonodectl",
        description=f"""geonodectl is a cmd client for the geonodev4 rest-apiv2.
To use this tool you have to set the following environment variables before starting:

{GEONODECTL_URL_ENV_VAR}: https://geonode.example.com/api/v2/ -- path to the v2 endpoint of your target geonode instance
{GEONODECTL_BASIC_ENV_VAR}: YWRtaW46YWRtaW4= -- you can generate this string like: echo -n user:password | base64
""",
        formatter_class=RawTextHelpFormatter,
    )

    ####################
    # GENERAL CMD ARGS #
    ####################

    # defining alias for add_parser https://gist.github.com/sampsyo/471779
    parser.register("action", "parsers", AliasedSubParsersAction)
    parser.add_argument(
        "--not-verify-ssl",
        dest="ssl_verify",
        default=False,
        action="store_true",
        help="allow to request domains with unsecure ssl certificates ...",
    )
    parser.add_argument(
        "--raw",
        "--json",
        dest="json",
        default=False,
        action="store_true",
        help="return output as raw response json as it comes from the rest API",
    )
    parser.add_argument(
        "--page-size",
        dest="page_size",
        default=DEFAULT_CMD_PAGE_SIZE,
        type=int,
        help="Number of results to return per page",
    )
    parser.add_argument(
        "--page",
        dest="page",
        default=DEFAULT_CMD_PAGE,
        type=int,
        help=" A page number within the paginated result set",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        dest="verbose",
        action="store_true",
        default=False,
        help="Enable verbose output",
    )

    subparsers = parser.add_subparsers(
        help="geonodectl commands", dest="command", required=True
    )

    #############################
    # RESOURCE ARGUMENT PARSING #
    #############################
    resource = subparsers.add_parser(
        "resources", help="resource commands", aliases=("resource",)
    )
    resource_subparsers = resource.add_subparsers(
        help="geonodectl resounrces commands", dest="subcommand", required=True
    )

    # LIST
    resource_list = resource_subparsers.add_parser("list", help="list resource")
    add_list_args(
        resource_list,
        "resources",
        ordering_default="date_updated",
        search_example="uuid",
    )
    # DELETE
    resource_delete = resource_subparsers.add_parser("delete", help="delete resource")
    add_pk_arg(resource_delete, "resource", "delete", multiple=True)
    # METADATA
    resource_metadata = resource_subparsers.add_parser(
        "metadata", help="download metadata for resource"
    )
    add_pk_arg(resource_metadata, "resource", "show metadata", metavar="{pk}")
    resource_metadata.add_argument(
        "--metadata-type",
        type=str,
        dest="metadata_type",
        choices=SUPPORTED_METADATA_TYPES,
        default=DEFAULT_METADATA_TYPE,
        help=f"metadata format to download (default: {DEFAULT_METADATA_TYPE})",
    )

    # VALIDATE
    add_validate_parser(resource_subparsers, "resource")

    ####################################
    # LINKED RESOURCE ARGUMENT PARSING #
    ####################################

    linked_resources = subparsers.add_parser(
        "linked-resources", help="handle linked resources for a resource"
    )
    linked_resource_subparsers = linked_resources.add_subparsers(
        help="geonodectl linked-resources commands", dest="subcommand", required=True
    )

    # DELETE
    linked_resource_delete_subparser = linked_resource_subparsers.add_parser(
        "delete",
        help="pks of resource to delete linked-resource from linked-to",
    )
    add_pk_arg(linked_resource_delete_subparser, "the resource")
    linked_resource_delete_subparser.add_argument(
        "--linked-to",
        nargs="+",
        dest="linked_to",
        type=str,
        required=False,
        help="space seperated list of resource pks or uuids to delete as linked-to (target) resources",
    )

    # ADD
    linked_resource_add_subparser = linked_resource_subparsers.add_parser(
        "add",
        help="pks of resources to add linked-resource as linked-to",
    )
    add_pk_arg(linked_resource_add_subparser, "the resource")
    linked_resource_add_subparser.add_argument(
        "--linked-to",
        nargs="+",
        dest="linked_to",
        type=str,
        required=False,
        help="space seperated list of resource pks or uuids to add as linked-to resources",
    )

    # DESCRIBE
    linked_resource_describe_subparser = linked_resource_subparsers.add_parser(
        "describe",
        help="list linked_resource of resource",
    )
    add_pk_arg(linked_resource_describe_subparser, "the resource")
    ####################################
    # ATTRIBUTE_TABLE ARGUMENT PARSING #
    ####################################

    attributes = subparsers.add_parser(
        "attributes",
        description="valid subcommands:",
        help="attribute commands",
        aliases=("attr", "attributes"),
    )
    attributes_subparsers = attributes.add_subparsers(
        help="geonodectl attribute commands", dest="subcommand", required=True
    )

    # DESCRIBE
    attributes_describe = attributes_subparsers.add_parser(
        "describe", help="describe attribute table"
    )
    add_pk_arg(attributes_describe, "dataset", "describe attributes of")
    # PATCH
    attributes_patch = attributes_subparsers.add_parser(
        "patch", help="patch attributes parameter values"
    )
    add_pk_arg(attributes_patch, "dataset", "patch")
    attributes_patch_mutually_exclusive_group = (
        attributes_patch.add_mutually_exclusive_group()
    )
    add_fields_arg(
        attributes_patch_mutually_exclusive_group,
        "patch parameters",
        '{"category": {"identifier": "farming"}}',
    )
    add_json_source_args(
        attributes_patch_mutually_exclusive_group, "the patch parameters"
    )

    ############################
    # DATASET ARGUMENT PARSING #
    ############################
    datasets = subparsers.add_parser(
        "dataset",
        description="valid subcommands:",
        help="dataset commands",
        aliases=("ds",),
    )
    datasets_subparsers = datasets.add_subparsers(
        help="geonodectl dataset commands", dest="subcommand", required=True
    )

    # LIST
    datasets_list = datasets_subparsers.add_parser("list", help="list datasets")
    add_list_args(
        datasets_list,
        "datasets",
        ordering_default="date_updated",
        search_example="water",
        filter_example="is_published=true owner.username=admin, or --filter title=test",
    )
    # UPLOAD
    datasets_upload = datasets_subparsers.add_parser(
        "upload", help="upload new datasets"
    )
    datasets_upload.add_argument(
        "-f",
        "--file",
        type=Path,
        dest="file_path",
        required=True,
        help="file to upload",
    )
    datasets_upload.add_argument(
        "--time",
        action="store_true",
        dest="time",
        default=False,
        help="uploads dataset as timeseries",
    )
    datasets_upload.add_argument(
        "--charset",
        type=str,
        dest="charset",
        default=DEFAULT_CHARSET,
        help="uploads dataset as timeseries",
    )
    datasets_upload.add_argument(
        "--mosaic",
        action="store_true",
        dest="mosaic",
        help="declare dataset upload as mosaic",
    )
    datasets_upload.add_argument(
        "--overwrite-existing-layer",
        action="store_true",
        dest="overwrite_existing_layer",
        help="set overwrite existing layer for upload",
    )
    datasets_upload.add_argument(
        "--skip-existing-layer",
        action="store_true",
        dest="skip_existing_layers",
        help="set skip existing layer for upload",
    )
    datasets_upload.add_argument(
        "--wait",
        action="store_true",
        dest="wait",
        default=False,
        help="wait for upload to finish and show resulting dataset(s)",
    )

    # PATCH
    datasets_patch = datasets_subparsers.add_parser(
        "patch", help="patch datasets metadata"
    )
    add_pk_arg(datasets_patch, "dataset", "patch", multiple=True)
    datasets_patch_mutually_exclusive_group = (
        datasets_patch.add_mutually_exclusive_group()
    )

    add_fields_arg(
        datasets_patch_mutually_exclusive_group,
        "patch metadata",
        '{"category": {"identifier": "farming"}}',
    )
    add_json_source_args(datasets_patch_mutually_exclusive_group, "the metadata")

    # DESCRIBE
    datasets_describe = datasets_subparsers.add_parser(
        "describe", help="get dataset details"
    )
    add_pk_arg(datasets_describe, "dataset", "describe", multiple=True)
    # DELETE
    datasets_delete = datasets_subparsers.add_parser(
        "delete", help="delete existing datasets"
    )
    add_pk_arg(datasets_delete, "dataset", "delete", multiple=True)
    # VALIDATE
    add_validate_parser(datasets_subparsers, "dataset")

    #############################
    # DOCUMENT ARGUMENT PARSING #
    #############################

    documents = subparsers.add_parser(
        "documents", help="document commands", aliases=("doc", "document")
    )
    documents_subparsers = documents.add_subparsers(
        help="geonodectl documents commands", dest="subcommand", required=True
    )

    # LIST
    documents_list = documents_subparsers.add_parser("list", help="list documents")
    add_list_args(
        documents_list,
        "document",
        ordering_default="date_updated",
        search_example="water",
        filter_example="is_published=true owner.username=admin, or --filter title=test",
    )
    # UPLOAD
    documents_upload = documents_subparsers.add_parser(
        "upload", help="upload new datasets"
    )
    documents_upload.add_argument(
        "-f",
        "--file",
        type=Path,
        dest="file_path",
        required=True,
        help="file to upload",
    )

    documents_upload.add_argument(
        "--metadata-only",
        action="store_true",
        dest="metadata_only",
        help="if set no landing page for the document will be generated, \
          but file is downloadable through link",
    )

    # PATCH
    documents_patch = documents_subparsers.add_parser(
        "patch", help="patch documents metadata"
    )
    add_pk_arg(documents_patch, "document", "patch", multiple=True)
    documents_patch_mutually_exclusive_group = (
        documents_patch.add_mutually_exclusive_group()
    )

    add_fields_arg(
        documents_patch_mutually_exclusive_group,
        "patch metadata",
        '{"category": {"identifier": "farming"}}',
    )
    add_json_source_args(documents_patch_mutually_exclusive_group, "the metadata")

    # DESCRIBE
    documents_describe = documents_subparsers.add_parser(
        "describe", help="get document details"
    )
    add_pk_arg(documents_describe, "document", "describe", multiple=True)
    # DELETE
    documents_delete = documents_subparsers.add_parser(
        "delete", help="delete existing document"
    )
    add_pk_arg(documents_delete, "document", "delete", multiple=True)
    # VALIDATE
    add_validate_parser(documents_subparsers, "document")

    ########################
    # MAP ARGUMENT PARSING #
    ########################
    maps = subparsers.add_parser("maps", help="maps commands")
    maps_subparsers = maps.add_subparsers(
        help="geonodectl maps commands", dest="subcommand", required=True
    )
    # LIST
    maps_list = maps_subparsers.add_parser("list", help="list documents")
    add_list_args(
        maps_list,
        "maps",
        ordering_default="date_updated",
        search_example="water",
        filter_example="is_published=true owner.username=admin, or --filter title=test",
    )
    # PATCH
    maps_patch = maps_subparsers.add_parser("patch", help="patch maps metadata")
    add_pk_arg(maps_patch, "map", "patch", multiple=True)
    maps_patch_mutually_exclusive_group = maps_patch.add_mutually_exclusive_group()

    add_fields_arg(
        maps_patch_mutually_exclusive_group,
        "patch metadata",
        '{"category": {"identifier": "farming"}}',
    )
    add_json_source_args(maps_patch_mutually_exclusive_group, "the metadata")

    # DESCRIBE
    maps_describe = maps_subparsers.add_parser("describe", help="get map details")
    add_pk_arg(maps_describe, "map", "describe", multiple=True)
    # DELETE
    maps_delete = maps_subparsers.add_parser("delete", help="delete existing map")
    add_pk_arg(maps_delete, "map", "delete", multiple=True)
    # CREATE
    maps_create = maps_subparsers.add_parser("create", help="create an (empty) map")

    maps_create_mutually_exclusive_group = maps_create.add_mutually_exclusive_group()
    maps_create_mutually_exclusive_group.add_argument(
        "--title",
        type=str,
        dest="title",
        help="title of the new dataset ...",
    )
    add_fields_arg(
        maps_create_mutually_exclusive_group,
        "add metadata",
        '{"category": {"identifier": "farming"}, "abstract": "test abstract"}',
    )
    add_json_source_args(maps_create_mutually_exclusive_group, "the metadata")

    maps_create.add_argument(
        "--maplayers",
        nargs="+",
        dest="maplayers",
        type=str,
        help="space seperated list of dataset pks or uuids to add as maplayer to the map",
    )

    # GET-BLOB
    maps_get_blob = maps_subparsers.add_parser(
        "get-blob", help="print the MapStore blob JSON for a map (pipe-friendly)"
    )
    add_pk_arg(maps_get_blob, "map", "fetch blob from")
    # SET-BLOB
    maps_set_blob = maps_subparsers.add_parser(
        "set-blob", help="replace the MapStore blob JSON for a map from a file"
    )
    add_pk_arg(maps_set_blob, "map", "update")
    maps_set_blob.add_argument(
        "--json_path",
        dest="json_path",
        type=str,
        required=True,
        help="read the new blob from a json file, given as a path or a http(s) url",
    )

    # MAPLAYERS
    maps_maplayers = maps_subparsers.add_parser(
        "maplayers", help="list, add or remove the maplayers of a map"
    )
    maps_maplayers_subparsers = maps_maplayers.add_subparsers(
        help="geonodectl maps maplayers commands",
        dest="maplayers_subcommand",
        required=True,
    )

    maps_maplayers_list = maps_maplayers_subparsers.add_parser(
        "list", help="list the maplayers of a map"
    )
    add_pk_arg(maps_maplayers_list, "map", "list maplayers of")
    maps_maplayers_add = maps_maplayers_subparsers.add_parser(
        "add", help="add datasets as maplayers to an existing map"
    )
    add_pk_arg(maps_maplayers_add, "map", "modify")
    maps_maplayers_add.add_argument(
        nargs="+",
        type=str,
        dest="datasets",
        help="space seperated list of dataset pks or uuids to add as maplayers to the map",
    )

    maps_maplayers_remove = maps_maplayers_subparsers.add_parser(
        "remove", help="remove maplayers from an existing map"
    )
    add_pk_arg(maps_maplayers_remove, "map", "modify")
    maps_maplayers_remove.add_argument(
        nargs="+",
        type=str,
        dest="datasets",
        help="space seperated list of dataset pks or uuids to remove as maplayers from the map",
    )

    # WIDGETS
    maps_widgets = maps_subparsers.add_parser(
        "widgets", help="list, add, describe or remove the widgets of a map"
    )
    maps_widgets_subparsers = maps_widgets.add_subparsers(
        help="geonodectl maps widgets commands",
        dest="widgets_subcommand",
        required=True,
    )

    maps_widgets_list = maps_widgets_subparsers.add_parser(
        "list", help="list the widgets of a map"
    )
    add_pk_arg(maps_widgets_list, "map", "list widgets of")
    maps_widgets_add = maps_widgets_subparsers.add_parser(
        "add", help="add a widget to an existing map"
    )
    add_pk_arg(maps_widgets_add, "map", "modify")
    maps_widgets_add.add_argument(
        nargs="?",
        default="textbox",
        choices=["textbox", "table"],
        dest="widget_type",
        help="type of widget to add (default: textbox)",
    )
    maps_widgets_add.add_argument(
        "--title", dest="title", type=str, default=None, help="title of the widget"
    )
    maps_widgets_add.add_argument(
        "--text",
        dest="text",
        type=str,
        default=None,
        help="textbox only: body of the widget, HTML is passed through to MapStore",
    )
    maps_widgets_add.add_argument(
        "--description",
        dest="description",
        type=str,
        default=None,
        help="table only: shown behind the info tool of the widget",
    )
    maps_widgets_add.add_argument(
        "--maplayer",
        dest="maplayer",
        type=str,
        default=None,
        help="table only: dataset pk of the maplayer to build the table from, \
            the same way maps maplayers add takes them. \
            has to be a maplayer of the map already",
    )
    maps_widgets_add.add_argument(
        "--attributes",
        nargs="+",
        dest="attributes",
        type=str,
        default=None,
        help="table only: space seperated list of attribute names to show as columns, \
            defaults to all attributes of the dataset",
    )
    maps_widgets_add.add_argument(
        "--attribute-ids",
        "--attribute_ids",
        nargs="+",
        dest="attribute_ids",
        type=int,
        default=None,
        help="table only: space seperated list of attribute pks to show as columns",
    )
    add_json_source_args(
        maps_widgets_add,
        "a raw widget definition",
        note="overrides --title and --text",
        dashed_alias=True,
    )

    maps_widgets_describe = maps_widgets_subparsers.add_parser(
        "describe", help="show a single widget of a map"
    )
    add_pk_arg(maps_widgets_describe, "map", "describe a widget of")
    maps_widgets_describe.add_argument(
        type=str, dest="widget_id", help="id of the widget to describe"
    )

    maps_widgets_remove = maps_widgets_subparsers.add_parser(
        "remove", help="remove a widget from an existing map"
    )
    add_pk_arg(maps_widgets_remove, "map", "modify")
    maps_widgets_remove.add_argument(
        type=str, dest="widget_id", help="id of the widget to remove"
    )

    # VALIDATE
    add_validate_parser(maps_subparsers, "map")

    ################################
    # GEOSERVER ARGUMENT PARSING   #
    ################################
    geoserver = subparsers.add_parser(
        "geoserver",
        help=f"GeoServer REST API commands — auth via {GEOSERVER_BASIC_AUTH_ENV_VAR} (Base64 user:pass) or {GEOSERVER_USER_ENV_VAR}+{GEOSERVER_PASSWORD_ENV_VAR}; URL defaults to {GEONODE_API_URL_ENV_VAR}",
    )
    geoserver_subparsers = geoserver.add_subparsers(
        help="geonodectl geoserver commands", dest="subcommand", required=True
    )

    geoserver_styles = geoserver_subparsers.add_parser(
        "styles", help="manage GeoServer styles"
    )
    geoserver_styles_subparsers = geoserver_styles.add_subparsers(
        help="geonodectl geoserver styles commands",
        dest="styles_subcommand",
        required=True,
    )

    # styles list
    geoserver_styles_list = geoserver_styles_subparsers.add_parser(
        "list", help="list styles in GeoServer"
    )
    geoserver_styles_list.add_argument(
        "--workspace",
        dest="workspace",
        type=str,
        required=False,
        default=None,
        help="limit to a specific GeoServer workspace, e.g. geonode",
    )

    # styles describe
    geoserver_styles_describe = geoserver_styles_subparsers.add_parser(
        "describe", help="print SLD XML for a style"
    )
    geoserver_styles_describe.add_argument(
        type=str, dest="name", help="style name in GeoServer"
    )
    geoserver_styles_describe.add_argument(
        "--workspace",
        dest="workspace",
        type=str,
        required=False,
        default=None,
        help="workspace the style belongs to",
    )

    # styles upload
    geoserver_styles_upload = geoserver_styles_subparsers.add_parser(
        "upload", help="create or update a style from an SLD file"
    )
    geoserver_styles_upload.add_argument(
        "--name",
        dest="name",
        type=str,
        required=True,
        help="style name in GeoServer",
    )
    geoserver_styles_upload.add_argument(
        "--sld-path",
        dest="sld_path",
        type=str,
        required=True,
        help="path to the SLD XML file to upload",
    )
    geoserver_styles_upload.add_argument(
        "--workspace",
        dest="workspace",
        type=str,
        default="geonode",
        help="target GeoServer workspace (default: geonode)",
    )

    # styles set-default
    geoserver_styles_set_default = geoserver_styles_subparsers.add_parser(
        "set-default", help="set the default style for a GeoServer layer"
    )
    geoserver_styles_set_default.add_argument(
        "--layer",
        dest="layer",
        type=str,
        required=True,
        help="fully qualified layer name, e.g. geonode:my_layer",
    )
    geoserver_styles_set_default.add_argument(
        "--style",
        dest="style_name",
        type=str,
        required=True,
        help="name of the style to set as default",
    )
    geoserver_styles_set_default.add_argument(
        "--workspace",
        dest="workspace",
        type=str,
        default="geonode",
        help="workspace of the style (default: geonode)",
    )

    ############################
    # GEOAPPS ARGUMENT PARSING #
    ############################
    geoapps = subparsers.add_parser(
        "geoapps", help="geoapps commands", aliases=("apps",)
    )
    geoapps_subparsers = geoapps.add_subparsers(
        help="geonodectl geoapps commands", dest="subcommand", required=True
    )

    # LIST
    geoapps_list = geoapps_subparsers.add_parser("list", help="list geoapps")
    add_list_args(
        geoapps_list,
        "geoapps",
        ordering_default="date_updated",
        search_example="water",
        filter_example="is_published=true owner.username=admin, or --filter title=test",
    )
    # PATCH
    geoapps_patch = geoapps_subparsers.add_parser(
        "patch", help="patch geoapps metadata"
    )
    add_pk_arg(geoapps_patch, "geoapp", "patch", multiple=True)
    geoapps_patch_mutually_exclusive_group = (
        geoapps_patch.add_mutually_exclusive_group()
    )
    add_fields_arg(
        geoapps_patch_mutually_exclusive_group,
        "patch metadata",
        '{"category": {"identifier": "farming"}}',
    )
    add_json_source_args(geoapps_patch_mutually_exclusive_group, "the metadata")

    # DESCRIBE
    geoapps_describe = geoapps_subparsers.add_parser(
        "describe", help="get geoapp details"
    )
    add_pk_arg(geoapps_describe, "geoapp", "describe", multiple=True)
    # DELETE
    geoapps_delete = geoapps_subparsers.add_parser(
        "delete", help="delete existing geoapp"
    )
    add_pk_arg(geoapps_delete, "geoapp", "delete", multiple=True)
    # VALIDATE
    add_validate_parser(geoapps_subparsers, "geoapp")

    ##########################
    # USERS ARGUMENT PARSING #
    ##########################
    users = subparsers.add_parser(
        "users", help="user | users commands", aliases=("user",)
    )
    users_subparsers = users.add_subparsers(
        help="geonodectl users commands", dest="subcommand", required=True
    )

    # PATCH
    users_patch = users_subparsers.add_parser("patch", help="patch users metadata")
    add_pk_arg(users_patch, "user", "patch", uuid=False)
    user_patch_mutually_exclusive_group = users_patch.add_mutually_exclusive_group()
    add_fields_arg(
        user_patch_mutually_exclusive_group,
        "patch metadata",
        '{"category": {"identifier": "farming"}}',
    )
    add_json_source_args(
        user_patch_mutually_exclusive_group, "the metadata (user credentials)"
    )

    # DESCRIBE
    users_describe = users_subparsers.add_parser("describe", help="get users details")
    add_pk_arg(users_describe, "user", "describe", uuid=False)
    users_describe_subgroup = users_describe.add_mutually_exclusive_group(
        required=False
    )
    users_describe_subgroup.add_argument(
        "--groups",
        dest="user_groups",
        required=False,
        action="store_true",
        help="show groups of user with given -pk ...",
    )
    users_describe_subgroup.add_argument(
        "--resources",
        dest="user_resources",
        required=False,
        action="store_true",
        help="show resources visible to the user with given -pk ...",
    )

    # LIST
    users_list = users_subparsers.add_parser("list", help="list documents")
    add_list_args(
        users_list,
        "users",
        ordering_default="pk",
        search_example="sven",
        filter_example="last_name=svenson or --filter username=svenson",
        ordering_example="username",
    )
    # DELETE
    users_delete = users_subparsers.add_parser("delete", help="delete existing user")
    add_pk_arg(users_delete, "user", "delete", multiple=True, uuid=False)
    # CREATE
    users_create = users_subparsers.add_parser("create", help="create a new user")
    user_create_mutually_exclusive_group = users_create.add_mutually_exclusive_group()
    user_create_mutually_exclusive_group.add_argument(
        "--username",
        type=str,
        dest="username",
        help="username of the new user ... (mutually exclusive [a])",
    )

    users_create.add_argument(
        "--email",
        type=str,
        required=False,
        dest="email",
        help="email of the new user ... (only working combined with --username) ...",
    )

    users_create.add_argument(
        "--first_name",
        type=str,
        required=False,
        dest="first_name",
        help="first_name of the new user (only working combined with --username) ...",
    )

    users_create.add_argument(
        "--last_name",
        type=str,
        required=False,
        dest="last_name",
        help="last_name of the new user (only working combined with --username) ...",
    )

    users_create.add_argument(
        "--is_superuser",
        action="store_true",
        required=False,
        dest="is_superuser",
        default=False,
        help="set to make the new user a superuser (only working combined with --username) ...",
    )

    users_create.add_argument(
        "--is_staff",
        action="store_true",
        required=False,
        dest="is_staff",
        default=False,
        help="set to make the new user a staff user (only working combined with --username) ...",
    )

    add_json_source_args(
        user_create_mutually_exclusive_group,
        "the metadata (user credentials)",
        note="mutually exclusive [b]",
    )

    add_fields_arg(
        user_create_mutually_exclusive_group,
        "create user",
        '{"username": "test_user", "email": "test@example.com", "first_name": "test_first_name", "last_name": "test_last_name", "is_staff": true, "is_superuser": true}',
        note="mutually exclusive [c]",
    )
    # TRANSFER RESOURCES
    users_transfer_resources = users_subparsers.add_parser(
        "transfer_resources", help="hand resources of a user over to another user"
    )
    add_pk_arg(
        users_transfer_resources, "the user currently owning the resources", uuid=False
    )
    users_transfer_resources.add_argument(
        "--new_owner",
        type=int,
        dest="new_owner",
        required=True,
        help="pk of the user to hand the resources to ...",
    )
    users_transfer_resources.add_argument(
        "--resources",
        nargs="+",
        type=str,
        dest="resources",
        help="pks of the resources to move, like --resources 1 2 3. Moves every resource \
        of the user if left out. Needs GeoNode 5, GeoNode 4.4 can only move all of them ...",
    )

    ###########################
    # GROUPS ARGUMENT PARSING #
    ###########################
    groups = subparsers.add_parser(
        "groups", help="group | groups commands", aliases=("group",)
    )
    groups_subparsers = groups.add_subparsers(
        help="geonodectl groups commands", dest="subcommand", required=True
    )

    # LIST
    groups_list = groups_subparsers.add_parser("list", help="list groups")
    add_list_args(
        groups_list,
        "groups",
        ordering_default="pk",
        search_example="mygroup",
        filter_example="title=mygroup",
    )
    # DESCRIBE
    groups_describe = groups_subparsers.add_parser("describe", help="get group details")
    add_pk_arg(groups_describe, "group", "describe", uuid=False)
    # PATCH
    groups_patch = groups_subparsers.add_parser("patch", help="patch group metadata")
    add_pk_arg(groups_patch, "group", "patch", uuid=False)
    groups_patch_mutually_exclusive_group = groups_patch.add_mutually_exclusive_group()
    add_fields_arg(
        groups_patch_mutually_exclusive_group,
        "patch metadata",
        '{"title": "new title"}',
    )
    add_json_source_args(groups_patch_mutually_exclusive_group, "the metadata")

    # CREATE
    groups_create = groups_subparsers.add_parser("create", help="create a new group")
    groups_create_mutually_exclusive_group = (
        groups_create.add_mutually_exclusive_group()
    )
    groups_create_mutually_exclusive_group.add_argument(
        "--title",
        type=str,
        dest="title",
        help="title of the new group ... (mutually exclusive [a])",
    )
    groups_create.add_argument(
        "--name",
        type=str,
        required=False,
        dest="name",
        help="slug name of the new group (only with --title) ...",
    )
    groups_create.add_argument(
        "--description",
        type=str,
        required=False,
        dest="description",
        default="",
        help="description of the new group (only with --title) ...",
    )
    add_json_source_args(
        groups_create_mutually_exclusive_group,
        "the group data",
        note="mutually exclusive [b]",
    )
    add_fields_arg(
        groups_create_mutually_exclusive_group,
        "create group",
        '{"title": "mygroup", "description": "my desc"}',
        note="mutually exclusive [c]",
    )
    # DELETE
    groups_delete = groups_subparsers.add_parser("delete", help="delete existing group")
    add_pk_arg(groups_delete, "group", "delete", multiple=True, uuid=False)
    ###########################
    # UPLOAD ARGUMENT PARSING #
    ###########################
    uploads = subparsers.add_parser("uploads", help="uploads commands")
    uploads_subparsers = uploads.add_subparsers(
        help="geonodectl uploads commands", dest="subcommand", required=True
    )

    # LIST
    uploads_list = uploads_subparsers.add_parser("list", help="list uploads")
    add_list_args(
        uploads_list,
        "uploads",
        ordering_default="date_updated",
        search_example="uuid",
        filter_example="title=test",
    )
    #####################################
    # EXECUTIONREQUEST ARGUMENT PARSING #
    #####################################
    executionrequest = subparsers.add_parser(
        "executionrequest", help="executionrequest commands"
    )
    executionrequest_subparsers = executionrequest.add_subparsers(
        help="geonodectl executionrequest commands", dest="subcommand", required=True
    )

    # LIST
    executionrequest_list = executionrequest_subparsers.add_parser(
        "list", help="list executionrequests"
    )
    add_list_args(
        executionrequest_list,
        "execution requests",
        ordering_default="created",
        search_example="uuid",
        filter_example="status=ready",
    )
    # DESCRIBE
    executionrequest_describe = executionrequest_subparsers.add_parser(
        "describe", help="get executionrequest details"
    )
    executionrequest_describe.add_argument(
        type=str, dest="exec_id", help="exec_id of executionrequest to describe ..."
    )

    ############################
    # KEYWORD ARGUMENT PARSING #
    ############################
    keywords = subparsers.add_parser("keywords", help="(Hierarchical) keyword commands")
    keywords_subparsers = keywords.add_subparsers(
        help="geonodectl keywords commands", dest="subcommand", required=True
    )

    # LIST
    keywords_list = keywords_subparsers.add_parser("list", help="list keywords")
    add_list_args(
        keywords_list,
        "keywords requests",
        ordering_default="id",
        search_example="uuid",
        filter_example="name=soil",
        ordering_example="name",
    )
    # DESCRIBE
    keywords_describe = keywords_subparsers.add_parser(
        "describe", help="get thesaurikeyword details"
    )
    # not fully clean to use pk here, as it is actually keyword but for now ...
    keywords_describe.add_argument(
        type=str, dest="pk", help="keyword of keywords to describe ..."
    )

    #####################################
    # THESAURI KEYWORD ARGUMENT PARSING #
    #####################################
    thesaurikeywords = subparsers.add_parser(
        "tkeywords", help="thesaurikeyword commands"
    )
    thesaurikeywords_subparsers = thesaurikeywords.add_subparsers(
        help="geonodectl thesaurikeywords commands", dest="subcommand", required=True
    )

    # LIST
    thesaurikeywords_list = thesaurikeywords_subparsers.add_parser(
        "list", help="list thesaurikeywords"
    )
    add_list_args(
        thesaurikeywords_list,
        "thesaurikeywords requests",
        ordering_default="keyword",
        search_example="uuid",
        filter_example="alt_label=soil",
        ordering_example="keyword",
    )
    # DESCRIBE
    thesaurikeywords_describe = thesaurikeywords_subparsers.add_parser(
        "describe", help="get thesaurikeyword details"
    )
    # not fully clean to use pk here, as it is actually keyword but for now ...
    thesaurikeywords_describe.add_argument(
        type=str, dest="pk", help="keyword of thesaurikeywords to describe ..."
    )

    ###########################################
    # THESAURI KEYWORD LABEL ARGUMENT PARSING #
    ###########################################
    thesaurikeywordlabels = subparsers.add_parser(
        "tkeywordlabels", help="thesaurikeywordlabel commands"
    )
    thesaurikeywordlabels_subparsers = thesaurikeywordlabels.add_subparsers(
        help="geonodectl thesaurikeywordlabels commands",
        dest="subcommand",
        required=True,
    )

    # LIST
    thesaurikeywordlabels_list = thesaurikeywordlabels_subparsers.add_parser(
        "list", help="list thesaurikeywordlabels"
    )
    add_list_args(
        thesaurikeywordlabels_list,
        "thesaurikeywordlabels requests",
        ordering_default="keyword",
        search_example="uuid",
        filter_example="lang=de label=Abbau",
        ordering_example="keyword",
    )
    # DESCRIBE
    hesaurikeywordlabels_describe = thesaurikeywordlabels_subparsers.add_parser(
        "describe", help="get thesaurikeywordlabels details"
    )
    # not fully clean to use pk here, as it is actually keyword but for now ...
    hesaurikeywordlabels_describe.add_argument(
        type=str, dest="pk", help="keyword of thesaurikeywordlabels to describe ..."
    )
    args = parser.parse_args()

    #####################
    # END OF ARGPARSING #
    #####################

    # configure logging
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG, force=True)
        logging.debug("Verbose mode enabled")
    else:
        logging.basicConfig(level=logging.INFO, force=True)
    try:
        url = os.environ[GEONODECTL_URL_ENV_VAR]
        basic = os.environ[GEONODECTL_BASIC_ENV_VAR]
    except KeyError:
        logging.error(
            f"Could not find one of the following envvars to rung geonodectl: {GEONODECTL_URL_ENV_VAR}, {GEONODECTL_BASIC_ENV_VAR} "
        )
        return EXIT_USAGE

    if not url.endswith("api/v2/"):
        logging.error(
            f"provided geonode url: {url} not ends with 'api/v2/'. Please make sure to provide full rest v2api url ..."
        )
        return EXIT_USAGE
    geonode_env = GeonodeApiConf(url=url, auth_basic=basic, verify=args.ssl_verify)
    g_obj: Union[GeonodeObjectHandler, GeonodeExecutionRequestHandler]
    match args.command:
        case "resources" | "resource":
            g_obj = GeonodeResourceHandler(env=geonode_env)
        case "linked_resources" | "linked-resources" | "linkedresources":
            g_obj = GeonodeLinkedResourcesHandler(env=geonode_env)
        case "attr" | "attribute" | "attributes":
            g_obj = GeonodeAttributeHandler(env=geonode_env)
        case "dataset" | "ds":
            g_obj = GeonodeDatasetsHandler(env=geonode_env)
        case "documents" | "doc" | "document":
            g_obj = GeonodeDocumentsHandler(env=geonode_env)
        case "maps":
            g_obj = GeonodeMapsHandler(env=geonode_env)
        case "users" | "user":
            g_obj = GeonodeUsersHandler(env=geonode_env)
        case "groups" | "group":
            g_obj = GeonodeGroupsHandler(env=geonode_env)
        case "geoapps" | "apps":
            g_obj = GeonodeGeoappsHandler(env=geonode_env)
        case "uploads":
            g_obj = GeonodeUploadsHandler(env=geonode_env)
        case "executionrequest" | "execrequest":
            g_obj = GeonodeExecutionRequestHandler(env=geonode_env)
        case "keywords" | "keywords":
            g_obj = GeonodeKeywordsRequestHandler(env=geonode_env)
        case "thesaurikeywords" | "tkeywords":
            g_obj = GeonodeThesauriKeywordsRequestHandler(env=geonode_env)
        case "thesaurikeywordlabels" | "tkeywordlabels":
            g_obj = GeonodeThesauriKeywordLabelsRequestHandler(env=geonode_env)
        case "geoserver":
            try:
                gs_handler = GeonodeGeoServerStyleHandler.from_env()
            except (KeyError, ValueError) as e:
                logging.error(
                    f"Cannot initialise GeoServer handler: {e}. "
                    f"Auth: set {GEOSERVER_BASIC_AUTH_ENV_VAR} (Base64 user:pass) "
                    f"or {GEOSERVER_USER_ENV_VAR}+{GEOSERVER_PASSWORD_ENV_VAR}. "
                    f"URL: set {GEOSERVER_URL_ENV_VAR} or {GEONODE_API_URL_ENV_VAR} "
                    f"(defaults to <geonode-base>/geoserver)."
                )
                return EXIT_USAGE
            if args.subcommand == "styles":
                gs_func = getattr(
                    gs_handler,
                    "cmd_style_" + args.styles_subcommand.replace("-", "_"),
                )
                return __exit_code__(gs_func(**args.__dict__))
            return EXIT_OK
        case _:
            raise NotImplementedError(f"unknown command: {args.command}")
    if args.command == "maps" and args.subcommand == "maplayers":
        g_obj_func = getattr(
            g_obj, "cmd_maplayers_" + args.maplayers_subcommand.replace("-", "_")
        )
        return __exit_code__(g_obj_func(**args.__dict__))
    if args.command == "maps" and args.subcommand == "widgets":
        g_obj_func = getattr(
            g_obj, "cmd_widgets_" + args.widgets_subcommand.replace("-", "_")
        )
        return __exit_code__(g_obj_func(**args.__dict__))
    g_obj_func = getattr(g_obj, "cmd_" + args.subcommand.replace("-", "_"))
    return __exit_code__(g_obj_func(**args.__dict__))


if __name__ == "__main__":
    sys.exit(geonodectl())
