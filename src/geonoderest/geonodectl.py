#!/usr/bin/env python3

import logging
import os
import sys
import argparse
from typing import List, Optional
from argparse import RawTextHelpFormatter
from pathlib import Path

from geonoderest.apiconf import GeonodeApiConf
from geonoderest.cliutils import (
    AliasedSubParsersAction,
    SubParsers,
    add_json_source_args,
    add_validate_parser,
    kwargs_append_action,
    route_subcommands,
)
from geonoderest.exceptions import GeoNodeRestException, GeonodeUsageError
from geonoderest.exitcodes import EXIT_FAILED, EXIT_OK, EXIT_USAGE
from geonoderest.extensions import (
    CommandRegistry,
    CommandSpec,
    GeonodeExtensionsHandler,
    build_registry,
)
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


#############################
# RESOURCE ARGUMENT PARSING #
#############################
def _build_resources_parser(resource: argparse.ArgumentParser) -> SubParsers:
    resource_subparsers = resource.add_subparsers(
        help="geonodectl resounrces commands", dest="subcommand", required=True
    )

    # LIST
    resource_list = resource_subparsers.add_parser("list", help="list resource")
    resource_list.add_argument(
        "--ordering",
        dest="ordering",
        default="date_updated",
        type=str,
        help="Which field to use when ordering the results. --ordering title (default: date_updated)",
    )
    resource_list.add_argument(
        "--search",
        dest="search",
        type=str,
        required=False,
        help="A search term to filter the results by. --search uuid",
    )

    # DELETE
    resource_delete = resource_subparsers.add_parser("delete", help="delete resource")
    resource_delete.add_argument(
        type=str,
        dest="pk",
        help="pk or uuid of resource(s) to delete (uuid, single '1', range '1-5', list '1,2,3') ...",
    )

    # METADATA
    resource_metadata = resource_subparsers.add_parser(
        "metadata", help="download metadata for resource"
    )
    resource_metadata.add_argument(
        type=str,
        dest="pk",
        metavar="{pk}",
        help="pk or uuid of resource to show metadata",
    )
    resource_metadata.add_argument(
        "--metadata-type",
        type=str,
        dest="metadata_type",
        choices=SUPPORTED_METADATA_TYPES,
        default=DEFAULT_METADATA_TYPE,
        help="pk or uuid of resource to show metadata",
    )

    # VALIDATE
    add_validate_parser(resource_subparsers, "resource")
    return resource_subparsers


####################################
# LINKED RESOURCE ARGUMENT PARSING #
####################################
def _build_linked_resources_parser(
    linked_resources: argparse.ArgumentParser,
) -> SubParsers:
    linked_resource_subparsers = linked_resources.add_subparsers(
        help="geonodectl linked-resources commands", dest="subcommand", required=True
    )

    # DELETE
    linked_resource_delete_subparser = linked_resource_subparsers.add_parser(
        "delete",
        help="pks of resource to delete linked-resource from linked-to",
    )
    linked_resource_delete_subparser.add_argument(
        type=str, dest="pk", help="pk or uuid of the resource ..."
    )

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
    linked_resource_add_subparser.add_argument(
        type=str, dest="pk", help="pk or uuid of the resource ..."
    )

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
    linked_resource_describe_subparser.add_argument(
        type=str, dest="pk", help="pk or uuid of the resource ..."
    )
    return linked_resource_subparsers


####################################
# ATTRIBUTE_TABLE ARGUMENT PARSING #
####################################
def _build_attributes_parser(attributes: argparse.ArgumentParser) -> SubParsers:
    attributes_subparsers = attributes.add_subparsers(
        help="geonodectl attribute commands", dest="subcommand", required=True
    )

    # DESCRIBE
    attributes_describe = attributes_subparsers.add_parser(
        "describe", help="describe attribute table"
    )
    attributes_describe.add_argument(
        type=str,
        dest="pk",
        help="pk or uuid of the dataset to describe attributes of ...",
    )

    # PATCH
    attributes_patch = attributes_subparsers.add_parser(
        "patch", help="patch attributes parameter values"
    )
    attributes_patch.add_argument(
        type=str, dest="pk", help="pk or uuid of dataset to patch"
    )
    attributes_patch_mutually_exclusive_group = (
        attributes_patch.add_mutually_exclusive_group()
    )
    attributes_patch_mutually_exclusive_group.add_argument(
        "--set",
        dest="fields",
        type=str,
        # TODO change example
        help='patch parameters by providing a json string like: \'{"category":{"identifier": "farming"}}\'',
    )
    add_json_source_args(
        attributes_patch_mutually_exclusive_group, "the patch parameters"
    )
    return attributes_subparsers


############################
# DATASET ARGUMENT PARSING #
############################
def _build_datasets_parser(datasets: argparse.ArgumentParser) -> SubParsers:
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
    datasets_list.add_argument(
        "--ordering",
        dest="ordering",
        default="date_updated",
        type=str,
        help="Which field to use when ordering the results. --ordering title (default: date_updated)",
    )
    datasets_list.add_argument(
        "--search",
        dest="search",
        type=str,
        required=False,
        help="A search term to filter the results by. --search water",
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
    datasets_patch.add_argument(
        type=str,
        dest="pk",
        help="pk or uuid of dataset(s) to patch (uuid, single '1', range '1-5', list '1,2,3') ...",
    )
    datasets_patch_mutually_exclusive_group = (
        datasets_patch.add_mutually_exclusive_group()
    )

    datasets_patch_mutually_exclusive_group.add_argument(
        "--set",
        dest="fields",
        type=str,
        help='patch metadata by providing a json string like: \'{"category":{"identifier": "farming"}}\'',
    )

    add_json_source_args(datasets_patch_mutually_exclusive_group, "the metadata")

    # DESCRIBE
    datasets_describe = datasets_subparsers.add_parser(
        "describe", help="get dataset details"
    )
    datasets_describe.add_argument(
        type=str,
        dest="pk",
        help="pk or uuid of dataset(s) to describe (uuid, single '1', range '1-5', list '1,2,3') ...",
    )

    # DELETE
    datasets_delete = datasets_subparsers.add_parser(
        "delete", help="delete existing datasets"
    )
    datasets_delete.add_argument(
        type=str,
        dest="pk",
        help="pk or uuid of dataset(s) to delete (uuid, single '1', range '1-5', list '1,2,3') ...",
    )

    # VALIDATE
    add_validate_parser(datasets_subparsers, "dataset")
    return datasets_subparsers


#############################
# DOCUMENT ARGUMENT PARSING #
#############################
def _build_documents_parser(documents: argparse.ArgumentParser) -> SubParsers:
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
        help="filter document by key value pairs. E.g. --filter \
          is_published=true owner.username=admin, or --filter title=test",
    )
    documents_list.add_argument(
        "--ordering",
        dest="ordering",
        default="date_updated",
        type=str,
        help="Which field to use when ordering the results. --ordering title (default: date_updated)",
    )
    documents_list.add_argument(
        "--search",
        dest="search",
        type=str,
        required=False,
        help="A search term to filter the results by. --search water",
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
    documents_patch.add_argument(
        type=str,
        dest="pk",
        help="pk or uuid of document(s) to patch (uuid, single '1', range '1-5', list '1,2,3') ...",
    )
    documents_patch_mutually_exclusive_group = (
        documents_patch.add_mutually_exclusive_group()
    )

    documents_patch_mutually_exclusive_group.add_argument(
        "--set",
        dest="fields",
        type=str,
        help='patch metadata by providing a json string like: \'{"category":"{"identifier": "farming"}}\'',
    )
    add_json_source_args(documents_patch_mutually_exclusive_group, "the metadata")

    # DESCRIBE
    documents_describe = documents_subparsers.add_parser(
        "describe", help="get document details"
    )
    documents_describe.add_argument(
        type=str,
        dest="pk",
        help="pk or uuid of document(s) to describe (uuid, single '1', range '1-5', list '1,2,3') ...",
    )

    # DELETE
    documents_delete = documents_subparsers.add_parser(
        "delete", help="delete existing document"
    )
    documents_delete.add_argument(
        type=str,
        dest="pk",
        help="pk or uuid of document(s) to delete (uuid, single '1', range '1-5', list '1,2,3') ...",
    )

    # VALIDATE
    add_validate_parser(documents_subparsers, "document")
    return documents_subparsers


########################
# MAP ARGUMENT PARSING #
########################
def _build_maps_parser(maps: argparse.ArgumentParser) -> SubParsers:
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
    maps_list.add_argument(
        "--ordering",
        dest="ordering",
        default="date_updated",
        type=str,
        help="Which field to use when ordering the results. --ordering title (default: date_updated)",
    )

    maps_list.add_argument(
        "--search",
        dest="search",
        type=str,
        required=False,
        help="A search term to filter the results by. --search water",
    )

    # PATCH
    maps_patch = maps_subparsers.add_parser("patch", help="patch maps metadata")
    maps_patch.add_argument(
        type=str,
        dest="pk",
        help="pk or uuid of map(s) to patch (uuid, single '1', range '1-5', list '1,2,3') ...",
    )
    maps_patch_mutually_exclusive_group = maps_patch.add_mutually_exclusive_group()

    maps_patch_mutually_exclusive_group.add_argument(
        "--set",
        dest="fields",
        type=str,
        help='patch metadata by providing a json string like: \'{"category":"{"identifier": "farming"}}\'',
    )
    add_json_source_args(maps_patch_mutually_exclusive_group, "the metadata")

    # DESCRIBE
    maps_describe = maps_subparsers.add_parser("describe", help="get map details")
    maps_describe.add_argument(
        type=str,
        dest="pk",
        help="pk or uuid of map(s) to describe (uuid, single '1', range '1-5', list '1,2,3') ...",
    )

    # DELETE
    maps_delete = maps_subparsers.add_parser("delete", help="delete existing map")
    maps_delete.add_argument(
        type=str,
        dest="pk",
        help="pk or uuid of map(s) to delete (uuid, single '1', range '1-5', list '1,2,3') ...",
    )

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
        help='add metadata by providing a json string like: \
          \'\'{ "category": {"identifier": "farming"}, "abstract": "test abstract" }\'\'',
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
    maps_get_blob.add_argument(
        type=str, dest="pk", help="pk or uuid of map to fetch blob from"
    )

    # SET-BLOB
    maps_set_blob = maps_subparsers.add_parser(
        "set-blob", help="replace the MapStore blob JSON for a map from a file"
    )
    maps_set_blob.add_argument(type=str, dest="pk", help="pk or uuid of map to update")
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
    maps_maplayers_list.add_argument(
        type=str, dest="pk", help="pk or uuid of map to list maplayers of"
    )

    maps_maplayers_add = maps_maplayers_subparsers.add_parser(
        "add", help="add datasets as maplayers to an existing map"
    )
    maps_maplayers_add.add_argument(
        type=str, dest="pk", help="pk or uuid of map to modify"
    )
    maps_maplayers_add.add_argument(
        nargs="+",
        type=str,
        dest="datasets",
        help="space seperated list of dataset pks or uuids to add as maplayers to the map",
    )

    maps_maplayers_remove = maps_maplayers_subparsers.add_parser(
        "remove", help="remove maplayers from an existing map"
    )
    maps_maplayers_remove.add_argument(
        type=str, dest="pk", help="pk or uuid of map to modify"
    )
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
    maps_widgets_list.add_argument(
        type=str, dest="pk", help="pk or uuid of map to list widgets of"
    )

    maps_widgets_add = maps_widgets_subparsers.add_parser(
        "add", help="add a widget to an existing map"
    )
    maps_widgets_add.add_argument(
        type=str, dest="pk", help="pk or uuid of map to modify"
    )
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
    maps_widgets_describe.add_argument(
        type=str, dest="pk", help="pk or uuid of map the widget belongs to"
    )
    maps_widgets_describe.add_argument(
        type=str, dest="widget_id", help="id of the widget to describe"
    )

    maps_widgets_remove = maps_widgets_subparsers.add_parser(
        "remove", help="remove a widget from an existing map"
    )
    maps_widgets_remove.add_argument(
        type=str, dest="pk", help="pk or uuid of map to modify"
    )
    maps_widgets_remove.add_argument(
        type=str, dest="widget_id", help="id of the widget to remove"
    )

    # VALIDATE
    add_validate_parser(maps_subparsers, "map")
    route_subcommands(maps_maplayers_subparsers, "cmd_maplayers_")
    route_subcommands(maps_widgets_subparsers, "cmd_widgets_")
    return maps_subparsers


################################
# GEOSERVER ARGUMENT PARSING   #
################################
def _build_geoserver_parser(geoserver: argparse.ArgumentParser) -> SubParsers:
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
    route_subcommands(geoserver_styles_subparsers, "cmd_style_")
    return geoserver_subparsers


############################
# GEOAPPS ARGUMENT PARSING #
############################
def _build_geoapps_parser(geoapps: argparse.ArgumentParser) -> SubParsers:
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
    geoapps_list.add_argument(
        "--ordering",
        dest="ordering",
        default="date_updated",
        type=str,
        help="Which field to use when ordering the results. --ordering title (default: date_updated)",
    )
    geoapps_list.add_argument(
        "--search",
        dest="search",
        type=str,
        required=False,
        help="A search term to filter the results by. --search water",
    )

    # PATCH
    geoapps_patch = geoapps_subparsers.add_parser(
        "patch", help="patch geoapps metadata"
    )
    geoapps_patch.add_argument(
        type=str,
        dest="pk",
        help="pk or uuid of geoapp(s) to patch (uuid, single '1', range '1-5', list '1,2,3') ...",
    )

    geoapps_patch_mutually_exclusive_group = (
        geoapps_patch.add_mutually_exclusive_group()
    )
    geoapps_patch_mutually_exclusive_group.add_argument(
        "--set",
        dest="fields",
        type=str,
        help='patch metadata by providing a json string like: \'{"category":"{"identifier": "farming"}}\'',
    )

    add_json_source_args(geoapps_patch_mutually_exclusive_group, "the metadata")

    # DESCRIBE
    geoapps_describe = geoapps_subparsers.add_parser(
        "describe", help="get geoapp details"
    )
    geoapps_describe.add_argument(
        type=str,
        dest="pk",
        help="pk or uuid of geoapp(s) to describe (uuid, single '1', range '1-5', list '1,2,3') ...",
    )

    # DELETE
    geoapps_delete = geoapps_subparsers.add_parser(
        "delete", help="delete existing geoapp"
    )
    geoapps_delete.add_argument(
        type=str,
        dest="pk",
        help="pk or uuid of geoapp(s) to delete (uuid, single '1', range '1-5', list '1,2,3') ...",
    )

    # VALIDATE
    add_validate_parser(geoapps_subparsers, "geoapp")
    return geoapps_subparsers


##########################
# USERS ARGUMENT PARSING #
##########################
def _build_users_parser(users: argparse.ArgumentParser) -> SubParsers:
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

    add_json_source_args(
        user_patch_mutually_exclusive_group, "the metadata (user credentials)"
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
    users_list.add_argument(
        "--ordering",
        dest="ordering",
        default="pk",
        type=str,
        help="Which field to use when ordering the results. --ordering username (default: pk)",
    )
    users_list.add_argument(
        "--search",
        dest="search",
        type=str,
        required=False,
        help="A search term to filter the results by. --search sven",
    )

    # DELETE
    users_delete = users_subparsers.add_parser("delete", help="delete existing user")
    users_delete.add_argument(
        type=str,
        dest="pk",
        help="pk of user(s) to delete (range '1-5',list '1,2,3,4,5', single '1') ...",
    )

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

    user_create_mutually_exclusive_group.add_argument(
        "--set",
        dest="fields",
        type=str,
        help='create user by providing a json string like: \'{"username":"test_user", \
        "email":"test_email@gmail.com", "first_name": "test_first_name", "last_name":"test_last_name",\
        "is_staff": true, "is_superuser": true}\' ... (mutually exclusive [c])',
    )

    # TRANSFER RESOURCES
    users_transfer_resources = users_subparsers.add_parser(
        "transfer_resources", help="hand resources of a user over to another user"
    )
    users_transfer_resources.add_argument(
        type=int, dest="pk", help="pk of the user currently owning the resources"
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
    return users_subparsers


###########################
# GROUPS ARGUMENT PARSING #
###########################
def _build_groups_parser(groups: argparse.ArgumentParser) -> SubParsers:
    groups_subparsers = groups.add_subparsers(
        help="geonodectl groups commands", dest="subcommand", required=True
    )

    # LIST
    groups_list = groups_subparsers.add_parser("list", help="list groups")
    groups_list.add_argument(
        "--filter",
        nargs="*",
        action=kwargs_append_action,
        dest="filter",
        type=str,
        help="filter groups by key value pairs. E.g. --filter title=mygroup",
    )
    groups_list.add_argument(
        "--ordering",
        dest="ordering",
        default="pk",
        type=str,
        help="Which field to use when ordering the results. --ordering title (default: pk)",
    )
    groups_list.add_argument(
        "--search",
        dest="search",
        type=str,
        required=False,
        help="A search term to filter the results by. --search mygroup",
    )

    # DESCRIBE
    groups_describe = groups_subparsers.add_parser("describe", help="get group details")
    groups_describe.add_argument(
        type=int, dest="pk", help="pk of group to describe ..."
    )

    # PATCH
    groups_patch = groups_subparsers.add_parser("patch", help="patch group metadata")
    groups_patch.add_argument(type=int, dest="pk", help="pk of group to patch")
    groups_patch_mutually_exclusive_group = groups_patch.add_mutually_exclusive_group()
    groups_patch_mutually_exclusive_group.add_argument(
        "--set",
        dest="fields",
        type=str,
        help='patch metadata by providing a json string like: \'{"title": "new title"}\' ',
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
    groups_create_mutually_exclusive_group.add_argument(
        "--set",
        dest="fields",
        type=str,
        help='create group by providing a json string like: \'{"title": "mygroup", "description": "my desc"}\' ... (mutually exclusive [c])',
    )

    # DELETE
    groups_delete = groups_subparsers.add_parser("delete", help="delete existing group")
    groups_delete.add_argument(
        type=str,
        dest="pk",
        help="pk of group(s) to delete (range '1-5', list '1,2,3', single '1') ...",
    )
    return groups_subparsers


###########################
# UPLOAD ARGUMENT PARSING #
###########################
def _build_uploads_parser(uploads: argparse.ArgumentParser) -> SubParsers:
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
    uploads_list.add_argument(
        "--ordering",
        dest="ordering",
        default="date_updated",
        type=str,
        help="Which field to use when ordering the results. --ordering title",
    )
    uploads_list.add_argument(
        "--search",
        dest="search",
        type=str,
        required=False,
        help="A search term to filter the results by. --search uuid",
    )
    return uploads_subparsers


#####################################
# EXECUTIONREQUEST ARGUMENT PARSING #
#####################################
def _build_executionrequest_parser(
    executionrequest: argparse.ArgumentParser,
) -> SubParsers:
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
    executionrequest_list.add_argument(
        "--ordering",
        dest="ordering",
        default="created",
        type=str,
        help="Which field to use when ordering the results. --ordering title (default: created)",
    )
    executionrequest_list.add_argument(
        "--search",
        dest="search",
        type=str,
        required=False,
        help="A search term to filter the results by. --search uuid",
    )

    # DESCRIBE
    executionrequest_describe = executionrequest_subparsers.add_parser(
        "describe", help="get executionrequest details"
    )
    executionrequest_describe.add_argument(
        type=str, dest="exec_id", help="exec_id of executionrequest to describe ..."
    )
    return executionrequest_subparsers


############################
# KEYWORD ARGUMENT PARSING #
############################
def _build_keywords_parser(keywords: argparse.ArgumentParser) -> SubParsers:
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
    keywords_list.add_argument(
        "--ordering",
        dest="ordering",
        default="id",
        type=str,
        help="Which field to use when ordering the results. --ordering name (default: id)",
    )
    keywords_list.add_argument(
        "--search",
        dest="search",
        type=str,
        required=False,
        help="A search term to filter the results by. --search uuid",
    )

    # DESCRIBE
    keywords_describe = keywords_subparsers.add_parser(
        "describe", help="get thesaurikeyword details"
    )
    # not fully clean to use pk here, as it is actually keyword but for now ...
    keywords_describe.add_argument(
        type=str, dest="pk", help="keyword of keywords to describe ..."
    )
    return keywords_subparsers


#####################################
# THESAURI KEYWORD ARGUMENT PARSING #
#####################################
def _build_thesaurikeywords_parser(
    thesaurikeywords: argparse.ArgumentParser,
) -> SubParsers:
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
    thesaurikeywords_list.add_argument(
        "--ordering",
        dest="ordering",
        default="keyword",
        type=str,
        help="Which field to use when ordering the results. --ordering keyword (default: keyword)",
    )
    thesaurikeywords_list.add_argument(
        "--search",
        dest="search",
        type=str,
        required=False,
        help="A search term to filter the results by. --search uuid",
    )

    # DESCRIBE
    thesaurikeywords_describe = thesaurikeywords_subparsers.add_parser(
        "describe", help="get thesaurikeyword details"
    )
    # not fully clean to use pk here, as it is actually keyword but for now ...
    thesaurikeywords_describe.add_argument(
        type=str, dest="pk", help="keyword of thesaurikeywords to describe ..."
    )
    return thesaurikeywords_subparsers


###############################
# EXTENSIONS ARGUMENT PARSING #
###############################
def _build_extensions_parser(extensions: argparse.ArgumentParser) -> SubParsers:
    extensions_subparsers = extensions.add_subparsers(
        help="geonodectl extensions commands", dest="subcommand", required=True
    )

    # LIST
    extensions_subparsers.add_parser(
        "list", help="list installed extensions and whether they loaded"
    )
    return extensions_subparsers


def _geoserver_handler(
    env: Optional[GeonodeApiConf] = None,
) -> GeonodeGeoServerStyleHandler:
    """build the GeoServer handler, it reads its own credentials from the env"""
    try:
        return GeonodeGeoServerStyleHandler.from_env()
    except (KeyError, ValueError) as e:
        raise GeonodeUsageError(
            f"Cannot initialise GeoServer handler: {e}. "
            f"Auth: set {GEOSERVER_BASIC_AUTH_ENV_VAR} (Base64 user:pass) "
            f"or {GEOSERVER_USER_ENV_VAR}+{GEOSERVER_PASSWORD_ENV_VAR}. "
            f"URL: set {GEOSERVER_URL_ENV_VAR} or {GEONODE_API_URL_ENV_VAR} "
            f"(defaults to <geonode-base>/geoserver)."
        )


def builtin_commands() -> List[CommandSpec]:
    """the commands geonodectl ships with, in the order --help lists them

    Extensions are registered after these, so a built-in always keeps its name
    (#133).
    """
    return [
        CommandSpec(
            name="resources",
            aliases=("resource",),
            help="resource commands",
            build_parser=_build_resources_parser,
            handler_factory=GeonodeResourceHandler,
        ),
        CommandSpec(
            name="linked-resources",
            help="handle linked resources for a resource",
            build_parser=_build_linked_resources_parser,
            handler_factory=GeonodeLinkedResourcesHandler,
        ),
        CommandSpec(
            name="attributes",
            aliases=("attr", "attributes"),
            help="attribute commands",
            description="valid subcommands:",
            build_parser=_build_attributes_parser,
            handler_factory=GeonodeAttributeHandler,
        ),
        CommandSpec(
            name="dataset",
            aliases=("ds",),
            help="dataset commands",
            description="valid subcommands:",
            build_parser=_build_datasets_parser,
            handler_factory=GeonodeDatasetsHandler,
        ),
        CommandSpec(
            name="documents",
            aliases=("doc", "document"),
            help="document commands",
            build_parser=_build_documents_parser,
            handler_factory=GeonodeDocumentsHandler,
        ),
        CommandSpec(
            name="maps",
            help="maps commands",
            build_parser=_build_maps_parser,
            handler_factory=GeonodeMapsHandler,
        ),
        CommandSpec(
            name="geoserver",
            help=f"GeoServer REST API commands — auth via {GEOSERVER_BASIC_AUTH_ENV_VAR} (Base64 user:pass) or {GEOSERVER_USER_ENV_VAR}+{GEOSERVER_PASSWORD_ENV_VAR}; URL defaults to {GEONODE_API_URL_ENV_VAR}",
            build_parser=_build_geoserver_parser,
            handler_factory=_geoserver_handler,
        ),
        CommandSpec(
            name="geoapps",
            aliases=("apps",),
            help="geoapps commands",
            build_parser=_build_geoapps_parser,
            handler_factory=GeonodeGeoappsHandler,
        ),
        CommandSpec(
            name="users",
            aliases=("user",),
            help="user | users commands",
            build_parser=_build_users_parser,
            handler_factory=GeonodeUsersHandler,
        ),
        CommandSpec(
            name="groups",
            aliases=("group",),
            help="group | groups commands",
            build_parser=_build_groups_parser,
            handler_factory=GeonodeGroupsHandler,
        ),
        CommandSpec(
            name="uploads",
            help="uploads commands",
            build_parser=_build_uploads_parser,
            handler_factory=GeonodeUploadsHandler,
        ),
        CommandSpec(
            name="executionrequest",
            help="executionrequest commands",
            build_parser=_build_executionrequest_parser,
            handler_factory=GeonodeExecutionRequestHandler,
        ),
        CommandSpec(
            name="keywords",
            help="(Hierarchical) keyword commands",
            build_parser=_build_keywords_parser,
            handler_factory=GeonodeKeywordsRequestHandler,
        ),
        CommandSpec(
            name="tkeywords",
            help="thesaurikeyword commands",
            build_parser=_build_thesaurikeywords_parser,
            handler_factory=GeonodeThesauriKeywordsRequestHandler,
        ),
        CommandSpec(
            name="extensions",
            help="list installed geonodectl extensions",
            build_parser=_build_extensions_parser,
            handler_factory=GeonodeExtensionsHandler,
            requires_env=False,
        ),
    ]


def build_parser(registry: CommandRegistry) -> argparse.ArgumentParser:
    """build the argument parser for every registered command

    Args:
        registry (CommandRegistry): built-in and extension commands

    Returns:
        argparse.ArgumentParser: the complete geonodectl parser
    """
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
    registry.build_parsers(subparsers)
    return parser


def __geonodectl__() -> int:
    registry = build_registry(builtin_commands())
    args = build_parser(registry).parse_args()

    # configure logging
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG, force=True)
        logging.debug("Verbose mode enabled")
    else:
        logging.basicConfig(level=logging.INFO, force=True)

    command = registry.resolve(args.command)
    if command is None:
        raise NotImplementedError(f"unknown command: {args.command}")

    geonode_env: Optional[GeonodeApiConf] = None
    if command.spec.requires_env:
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
    return __exit_code__(command.run(geonode_env, vars(args)))


if __name__ == "__main__":
    sys.exit(geonodectl())
