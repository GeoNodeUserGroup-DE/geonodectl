import argparse
import os
import sys
import logging
from geonoderest.resources_handler import ResourceHandler
from geonoderest.datasets_handler import DatasetsHandler
from geonoderest.users_handler import UsersHandler
from geonoderest.documents_handler import DocumentsHandler
from geonoderest.maps_handler import MapsHandler
from geonoderest.geoapps_handler import GeoappsHandler
from geonoderest.uploads_handler import UploadsHandler
from geonoderest.keywords_handler import KeywordsHandler
from geonoderest.tkeywords_handler import TKeywordsHandler
from geonoderest.tkeywordlabels_handler import TKeywordLabelsHandler
from geonoderest.attributes_handler import AttributesHandler
from geonoderest.linkedresources_handler import LinkedResourcesHandler
from geonoderest.executionrequest_handler import ExecutionRequestHandler

GEONODECTL_URL_ENV_VAR = "GEONODE_API_URL"
GEONODECTL_BASIC_ENV_VAR = "GEONODE_API_BASIC_AUTH"

HANDLER_MAP = {
    "resources": ResourceHandler,
    "datasets": DatasetsHandler,
    "users": UsersHandler,
    "documents": DocumentsHandler,
    "maps": MapsHandler,
    "geoapps": GeoappsHandler,
    "uploads": UploadsHandler,
    "keywords": KeywordsHandler,
    "tkeywords": TKeywordsHandler,
    "tkeywordlabels": TKeywordLabelsHandler,
    "attributes": AttributesHandler,
    "linked-resources": LinkedResourcesHandler,
    "executionrequest": ExecutionRequestHandler,
}


def main():
    parser = argparse.ArgumentParser(description="geonodectl (capability pattern)")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Dynamically add subcommands for each handler
    for cmd, handler_cls in HANDLER_MAP.items():
        cmd_parser = subparsers.add_parser(cmd, help=f"{cmd} commands")
        cmd_subparsers = cmd_parser.add_subparsers(dest="subcommand", required=True)
        # Add common subcommands based on handler methods
        handler = handler_cls({})  # dummy env for introspection
        if hasattr(handler, "list"):
            cmd_subparsers.add_parser("list", help=f"List {cmd}")
        if hasattr(handler, "delete"):
            cmd_subparsers.add_parser("delete", help=f"Delete {cmd}").add_argument(
                "pk", type=str
            )
        if hasattr(handler, "describe"):
            cmd_subparsers.add_parser("describe", help=f"Describe {cmd}").add_argument(
                "pk", type=int
            )
        if hasattr(handler, "patch"):
            cmd_subparsers.add_parser("patch", help=f"Patch {cmd}").add_argument(
                "pk", type=int
            )
        if hasattr(handler, "cmd_upload"):
            upload_parser = cmd_subparsers.add_parser(
                "upload", help=f"Upload for {cmd}"
            )
            upload_parser.add_argument("file_path", type=str)
            upload_parser.add_argument("--charset", type=str, default="UTF-8")
            upload_parser.add_argument("--time", action="store_true")
            upload_parser.add_argument("--mosaic", action="store_true")
            upload_parser.add_argument(
                "--overwrite_existing_layer", action="store_true"
            )
            upload_parser.add_argument("--skip_existing_layers", action="store_true")
        if hasattr(handler, "cmd_metadata"):
            meta_parser = cmd_subparsers.add_parser(
                "metadata", help=f"Download metadata for {cmd}"
            )
            meta_parser.add_argument("pk", type=int)
            meta_parser.add_argument("--metadata_type", type=str, default="ISO")
        if hasattr(handler, "cmd_create"):
            create_parser = cmd_subparsers.add_parser(
                "create", help=f"Create for {cmd}"
            )
            create_parser.add_argument("--username", type=str)
            create_parser.add_argument("--email", type=str, default="")
            create_parser.add_argument("--first_name", type=str, default="")
            create_parser.add_argument("--last_name", type=str, default="")
            create_parser.add_argument("--is_superuser", action="store_true")
            create_parser.add_argument("--is_staff", action="store_true")
            create_parser.add_argument("--fields", type=str)
            create_parser.add_argument("--json_path", type=str)

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if getattr(args, "verbose", False) else logging.INFO
    )

    try:
        url = os.environ[GEONODECTL_URL_ENV_VAR]
        basic = os.environ[GEONODECTL_BASIC_ENV_VAR]
    except KeyError:
        logging.error(
            f"Missing env vars: {GEONODECTL_URL_ENV_VAR}, {GEONODECTL_BASIC_ENV_VAR}"
        )
        sys.exit(1)

    env = dict(url=url, basic=basic)

    handler_cls = HANDLER_MAP.get(args.command)
    if not handler_cls:
        parser.error(f"Unknown command: {args.command}")
    handler = handler_cls(env)

    try:
        if args.subcommand == "list" and hasattr(handler, "list"):
            print(handler.list())
        elif args.subcommand == "delete" and hasattr(handler, "delete"):
            print(handler.delete(args.pk))
        elif args.subcommand == "describe" and hasattr(handler, "describe"):
            print(handler.describe(args.pk))
        elif args.subcommand == "patch" and hasattr(handler, "patch"):
            print(handler.patch(args.pk, {}))
        elif args.subcommand == "upload" and hasattr(handler, "cmd_upload"):
            print(
                handler.cmd_upload(
                    file_path=args.file_path,
                    charset=getattr(args, "charset", "UTF-8"),
                    time=getattr(args, "time", False),
                    mosaic=getattr(args, "mosaic", False),
                    overwrite_existing_layer=getattr(
                        args, "overwrite_existing_layer", False
                    ),
                    skip_existing_layers=getattr(args, "skip_existing_layers", False),
                )
            )
        elif args.subcommand == "metadata" and hasattr(handler, "cmd_metadata"):
            print(
                handler.cmd_metadata(
                    args.pk, metadata_type=getattr(args, "metadata_type", "ISO")
                )
            )
        elif args.subcommand == "create" and hasattr(handler, "cmd_create"):
            print(
                handler.cmd_create(
                    username=getattr(args, "username", None),
                    email=getattr(args, "email", ""),
                    first_name=getattr(args, "first_name", ""),
                    last_name=getattr(args, "last_name", ""),
                    is_superuser=getattr(args, "is_superuser", False),
                    is_staff=getattr(args, "is_staff", False),
                    fields=getattr(args, "fields", None),
                    json_path=getattr(args, "json_path", None),
                )
            )
        else:
            parser.error(
                f"Unknown or unsupported subcommand: {args.subcommand} for {args.command}"
            )
    except Exception as e:
        import requests

        if isinstance(e, requests.RequestException):
            print(f"HTTP error: {e}", file=sys.stderr)
            sys.exit(2)
        elif isinstance(e, (ValueError, TypeError)):
            print(f"Argument error: {e}", file=sys.stderr)
            sys.exit(3)
        else:
            print(f"Unexpected error: {e}", file=sys.stderr)
            sys.exit(99)


if __name__ == "__main__":
    main()
