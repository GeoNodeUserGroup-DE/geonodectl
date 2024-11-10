#!/usr/bin/env python3

import logging
import os
import sys
import argparse
from typing import List, Union
from argparse import RawTextHelpFormatter
from pathlib import Path

from .apiconf import GeonodeApiConf
from .geonodeobject import GeonodeObjectHandler
from .datasets import GeonodeDatasetsHandler
from .resources import (
    GeonodeResourceHandler,
    SUPPORTED_METADATA_TYPES,
    DEFAULT_METADATA_TYPE,
)
from .documents import GeonodeDocumentsHandler
from .maps import GeonodeMapsHandler
from .users import GeonodeUsersHandler
from .geoapps import GeonodeGeoappsHandler
from .uploads import GeonodeUploadsHandler
from .executionrequest import GeonodeExecutionRequestHandler
from .tkeywords import GeonodeThesauriKeywordsRequestHandler
from .tkeywordlabels import GeonodeThesauriKeywordLabelsRequestHandler


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
        except ValueError as ex:
            raise argparse.ArgumentError(
                self,
                f'Could not parse argument "{values}" as field_name1=new_value1 field_name2=new_value2 ... format',
            )
        setattr(args, self.dest, d)


def geonodectl():
    logging.basicConfig(level=logging.INFO)
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
    resource_subparsers.add_parser("list", help="list resource")

    # DELETE
    resource_delete = resource_subparsers.add_parser("delete", help="delete resource")
    resource_delete.add_argument(type=str, dest="pk", help="pk of resource to delete")

    # METADATA
    resource_metadata = resource_subparsers.add_parser(
        "metadata", help="download metadata for resource"
    )
    resource_metadata.add_argument(
        type=int,
        dest="pk",
        metavar="{pk}",
        help="pk of resource to show metadata",
    )
    resource_metadata.add_argument(
        "--metadata-type",
        type=str,
        dest="metadata_type",
        choices=SUPPORTED_METADATA_TYPES,
        default=DEFAULT_METADATA_TYPE,
        help="pk of resource to show metadata",
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
    datasets_list.add_argument(
        "--filter",
        nargs="*",
        action=kwargs_append_action,
        dest="filter",
        type=str,
        help="filter datasets by key value pairs. E.g. --filter is_published=true owner.username=admin, or --filter title=test",
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

    # PATCH
    datasets_patch = datasets_subparsers.add_parser(
        "patch", help="patch datasets metadata"
    )
    datasets_patch.add_argument(type=int, dest="pk", help="pk of dataset to patch")
    datasets_patch_mutually_exclusive_group = (
        datasets_patch.add_mutually_exclusive_group()
    )

    datasets_patch_mutually_exclusive_group.add_argument(
        "--set",
        dest="fields",
        type=str,
        help='patch metadata by providing a json string like: \'{"category":"{"identifier": "farming"}}\'',
    )

    datasets_patch_mutually_exclusive_group.add_argument(
        "--json_path",
        dest="json_path",
        type=str,
        help="patch metadata by providing a path to a json file",
    )

    # DESCRIBE
    datasets_describe = datasets_subparsers.add_parser(
        "describe", help="get dataset details"
    )
    datasets_describe.add_argument(
        type=int, dest="pk", help="pk of dataset to describe ..."
    )

    # DELETE
    datasets_delete = datasets_subparsers.add_parser(
        "delete", help="delete existing datasets"
    )
    datasets_delete.add_argument(
        type=str, dest="pk", help="pk of dataset to delete ..."
    )

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
    documents_list.add_argument(
        "--filter",
        nargs="*",
        action=kwargs_append_action,
        dest="filter",
        type=str,
        help="filter document by key value pairs. E.g. --filter is_published=true owner.username=admin, or --filter title=test",
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
        help="if set no landing page for the document will be generated, but file is downloadable through link",
    )

    # PATCH
    documents_patch = documents_subparsers.add_parser(
        "patch", help="patch documents metadata"
    )
    documents_patch.add_argument(type=int, dest="pk", help="pk of documents to patch")
    documents_patch_mutually_exclusive_group = (
        documents_patch.add_mutually_exclusive_group()
    )

    documents_patch_mutually_exclusive_group.add_argument(
        "--set",
        dest="fields",
        type=str,
        help='patch metadata by providing a json string like: \'{"category":"{"identifier": "farming"}}\'',
    )
    documents_patch_mutually_exclusive_group.add_argument(
        "--json_path",
        dest="json_path",
        type=str,
        help="add metadata by providing a path to a json file",
    )

    # DESCRIBE
    documents_describe = documents_subparsers.add_parser(
        "describe", help="get document details"
    )
    documents_describe.add_argument(
        type=int, dest="pk", help="pk of document to describe ..."
    )

    # DELETE
    documents_delete = documents_subparsers.add_parser(
        "delete", help="delete existing document"
    )
    documents_delete.add_argument(
        type=str, dest="pk", help="pk of document to delete ..."
    )

    ########################
    # MAP ARGUMENT PARSING #
    ########################
    maps = subparsers.add_parser("maps", help="maps commands")
    maps_subparsers = maps.add_subparsers(
        help="geonodectl maps commands", dest="subcommand", required=True
    )
    # LIST
    maps_list = maps_subparsers.add_parser("list", help="list documents")
    maps_list.add_argument(
        "--filter",
        nargs="*",
        action=kwargs_append_action,
        dest="filter",
        type=str,
        help="filter maps by key value pairs. E.g. --filter is_published=true owner.username=admin, or --filter title=test",
    )
    # PATCH
    maps_patch = maps_subparsers.add_parser("patch", help="patch maps metadata")
    maps_patch.add_argument(type=int, dest="pk", help="pk of map to patch")
    maps_patch_mutually_exclusive_group = maps_patch.add_mutually_exclusive_group()

    maps_patch_mutually_exclusive_group.add_argument(
        "--set",
        dest="fields",
        type=str,
        help='patch metadata by providing a json string like: \'{"category":"{"identifier": "farming"}}\'',
    )
    maps_patch_mutually_exclusive_group.add_argument(
        "--json_path",
        dest="json_path",
        type=str,
        help="add metadata by providing a path to a json file",
    )

    # DESCRIBE
    maps_describe = maps_subparsers.add_parser("describe", help="get map details")
    maps_describe.add_argument(type=int, dest="pk", help="pk of map to describe ...")

    # DELETE
    maps_delete = maps_subparsers.add_parser("delete", help="delete existing map")
    maps_delete.add_argument(type=str, dest="pk", help="pk of map to delete ...")

    # CREATE
    maps_create = maps_subparsers.add_parser("create", help="create an (empty) map")

    maps_create_mutually_exclusive_group = maps_create.add_mutually_exclusive_group()
    maps_create_mutually_exclusive_group.add_argument(
        "--title",
        type=str,
        dest="title",
        help="title of the new dataset ...",
    )
    maps_create_mutually_exclusive_group.add_argument(
        "--set",
        dest="fields",
        type=str,
        help='add metadata by providing a json string like: \'\'{ "category": {"identifier": "farming"}, "abstract": "test abstract" }\'\'',
    )

    maps_create_mutually_exclusive_group.add_argument(
        "--json_path",
        dest="json_path",
        type=str,
        help="add metadata by providing a path to a json file",
    )

    maps_create.add_argument(
        "--maplayers",
        nargs="+",
        dest="maplayers",
        type=int,
        help="space seperate list of integers of pks to add as maplayer to the map",
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
    geoapps_list.add_argument(
        "--filter",
        nargs="*",
        action=kwargs_append_action,
        dest="filter",
        type=str,
        help="filter geoapps by key value pairs. E.g. --filter is_published=true owner.username=admin, or --filter title=test",
    )
    # PATCH
    geoapps_patch = geoapps_subparsers.add_parser(
        "patch", help="patch geoapps metadata"
    )
    geoapps_patch.add_argument(type=int, dest="pk", help="pk of geoapp to patch")

    geoapps_patch_mutually_exclusive_group = (
        geoapps_patch.add_mutually_exclusive_group()
    )
    geoapps_patch_mutually_exclusive_group.add_argument(
        "--set",
        dest="fields",
        type=str,
        help='patch metadata by providing a json string like: \'{"category":"{"identifier": "farming"}}\'',
    )

    geoapps_patch_mutually_exclusive_group.add_argument(
        "--json_path",
        dest="json_path",
        type=str,
        help="patch metadata (user credentials) by providing a path to a json file, like --set written in file ...",
    )

    # DESCRIBE
    geoapps_describe = geoapps_subparsers.add_parser(
        "describe", help="get geoapp details"
    )
    geoapps_describe.add_argument(
        type=int, dest="pk", help="pk of geoapp to describe ..."
    )

    # DELETE
    geoapps_delete = geoapps_subparsers.add_parser(
        "delete", help="delete existing geoapp"
    )
    geoapps_delete.add_argument(type=str, dest="pk", help="pk of geoapp to delete ...")

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
    users_patch.add_argument(type=int, dest="pk", help="pk of user to patch")

    user_patch_mutually_exclusive_group = users_patch.add_mutually_exclusive_group()
    user_patch_mutually_exclusive_group.add_argument(
        "--set",
        dest="fields",
        type=str,
        help='patch metadata by providing a json string like: \'{"category":"{"identifier": "farming"}}\'',
    )

    user_patch_mutually_exclusive_group.add_argument(
        "--json_path",
        dest="json_path",
        type=str,
        help="patch metadata (user credentials) by providing a path to a json file, like --set written in file ...",
    )

    # DESCRIBE
    users_describe = users_subparsers.add_parser("describe", help="get users details")
    users_describe.add_argument(type=int, dest="pk", help="pk of users to describe ...")
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
    users_list.add_argument(
        "--filter",
        nargs="*",
        action=kwargs_append_action,
        dest="filter",
        type=str,
        help="filter users by key value pairs. E.g. --filter last_name=svenson or --filter username=svenson",
    )
    # DELETE
    users_delete = users_subparsers.add_parser("delete", help="delete existing user")
    users_delete.add_argument(type=str, dest="pk", help="pk of geoapp to delete ...")

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

    user_create_mutually_exclusive_group.add_argument(
        "--json_path",
        dest="json_path",
        type=str,
        help="add metadata (user credentials) by providing a path to a json file, like --set written in file ...(mutually exclusive [b])",
    )

    user_create_mutually_exclusive_group.add_argument(
        "--set",
        dest="fields",
        type=str,
        help='create user by providing a json string like: \'{"username":"test_user", "email":"test_email@gmail.com", "first_name": "test_first_name", "last_name":"test_last_name", "is_staff": true, "is_superuser": true}\' ... (mutually exclusive [c])',
    )

    ###########################
    # UPLOAD ARGUMENT PARSING #
    ###########################
    uploads = subparsers.add_parser("uploads", help="uploads commands")
    uploads_subparsers = uploads.add_subparsers(
        help="geonodectl uploads commands", dest="subcommand", required=True
    )

    # LIST
    uploads_list = uploads_subparsers.add_parser("list", help="list uploads")
    uploads_list.add_argument(
        "--filter",
        nargs="*",
        action=kwargs_append_action,
        dest="filter",
        type=str,
        help="filter uploads by key value pairs. E.g. --filter title=test",
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
    executionrequest_list.add_argument(
        "--filter",
        nargs="*",
        action=kwargs_append_action,
        dest="filter",
        type=str,
        help="filter execution requests by key value pairs. E.g. --filter status=ready",
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
    keywords_list.add_argument(
        "--filter",
        nargs="*",
        action=kwargs_append_action,
        dest="filter",
        type=str,
        help="filter keywords requests by key value pairs. E.g. --filter name=soil",
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
    thesaurikeywords_list.add_argument(
        "--filter",
        nargs="*",
        action=kwargs_append_action,
        dest="filter",
        type=str,
        help="filter thesaurikeywords requests by key value pairs. E.g. --filter alt_label=soil",
    )
    # DESCRIBE
    thesaurikeywords_describe = thesaurikeywords_subparsers.add_parser(
        "describe", help="get thesaurikeyword details"
    )
    # not fully clean to use pk here, as it is actually keyword but for now ...
    thesaurikeywords_describe.add_argument(
        type=str, dest="pk", help="keyword of thesaurikeywords to describe ..."
    )

    #####################################
    # THESAURI KEYWORD LABEL ARGUMENT PARSING #
    #####################################
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
    thesaurikeywordlabels_list.add_argument(
        "--filter",
        nargs="*",
        action=kwargs_append_action,
        dest="filter",
        type=str,
        help="filter thesaurikeywordlabels requests by key value pairs. E.g. --filter lang=de label=Abbau",
    )
    # DESCRIBE
    hesaurikeywordlabels_describe = thesaurikeywordlabels_subparsers.add_parser(
        "describe", help="get thesaurikeywordlabels details"
    )
    # not fully clean to use pk here, as it is actually keyword but for now ...
    hesaurikeywordlabels_describe.add_argument(
        type=str, dest="pk", help="keyword of thesaurikeywordlabels to describe ..."
    )

    #####################
    # END OF ARGPARSING #
    #####################

    args = parser.parse_args()
    try:
        url = os.environ[GEONODECTL_URL_ENV_VAR]
        basic = os.environ[GEONODECTL_BASIC_ENV_VAR]
    except KeyError:
        logging.error(
            f"Could not find one of the following envvars to rung geonodectl: {GEONODECTL_URL_ENV_VAR}, {GEONODECTL_BASIC_ENV_VAR} "
        )
        sys.exit(1)

    if not url.endswith("api/v2/"):
        raise NameError(
            f"provided geonode url: {url} not ends with 'api/v2/'. Please make sure to provide full rest v2api url ..."
        )

    geonode_env = GeonodeApiConf(url=url, auth_basic=basic, verify=args.ssl_verify)
    g_obj: Union[GeonodeObjectHandler, GeonodeExecutionRequestHandler]
    match args.command:
        case "resources" | "resource":
            g_obj = GeonodeResourceHandler(env=geonode_env)
        case "dataset" | "ds":
            g_obj = GeonodeDatasetsHandler(env=geonode_env)
        case "documents" | "doc" | "document":
            g_obj = GeonodeDocumentsHandler(env=geonode_env)
        case "maps":
            g_obj = GeonodeMapsHandler(env=geonode_env)
        case "users" | "user":
            g_obj = GeonodeUsersHandler(env=geonode_env)
        case "geoapps" | "apps":
            g_obj = GeonodeGeoappsHandler(env=geonode_env)
        case "uploads":
            g_obj = GeonodeUploadsHandler(env=geonode_env)
        case "executionrequest" | "execrequest":
            g_obj = GeonodeExecutionRequestHandler(env=geonode_env)
        case "thesaurikeywords" | "tkeywords":
            g_obj = GeonodeThesauriKeywordsRequestHandler(env=geonode_env)
        case "thesaurikeywordlabels" | "tkeywordlabels":
            g_obj = GeonodeThesauriKeywordLabelsRequestHandler(env=geonode_env)

        case _:
            raise NotImplemented
    g_obj_func = getattr(g_obj, "cmd_" + args.subcommand)
    g_obj_func(**args.__dict__)


if __name__ == "__main__":
    sys.exit(geonodectl())
