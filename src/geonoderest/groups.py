import json
import sys
import logging
from typing import Dict, List, Optional

from geonoderest.geonodeobject import GeonodeObjectHandler
from geonoderest.geonodetypes import GeonodeCmdOutListKey
from geonoderest.cmdprint import (
    print_json,
    json_decode_error_handler,
)


class GeonodeGroupsHandler(GeonodeObjectHandler):
    ENDPOINT_NAME = "groups"
    JSON_OBJECT_NAME = "groups"
    SINGULAR_RESOURCE_NAME = "group"

    LIST_CMDOUT_HEADER: List[GeonodeCmdOutListKey] = [
        GeonodeCmdOutListKey(key="pk"),
        GeonodeCmdOutListKey(key="title"),
        GeonodeCmdOutListKey(key="name"),
        GeonodeCmdOutListKey(key="description"),
    ]

    def get(self, pk: int, **kwargs) -> Optional[Dict]:
        """Get details for a given group pk.

        Args:
            pk (int): pk of the group

        Returns:
            Dict: group details
        """
        r = self.http_get(endpoint=f"{self.ENDPOINT_NAME}/{pk}")
        if r is None:
            return None
        return r[self.SINGULAR_RESOURCE_NAME]

    def cmd_create(
        self,
        title: Optional[str] = None,
        name: Optional[str] = None,
        description: str = "",
        fields: Optional[str] = None,
        json_path: Optional[str] = None,
        **kwargs,
    ):
        """Create a new group and print the result.

        Args:
            title (Optional[str]): Title of the group.
            name (Optional[str]): Slug/name identifier for the group.
            description (str): Description of the group.
            fields (Optional[str]): JSON string with group data.
            json_path (Optional[str]): Path to a JSON file with group data.
        """
        json_content = None
        if json_path:
            with open(json_path, "r") as file:
                try:
                    json_content = json.load(file)
                except json.decoder.JSONDecodeError as E:
                    json_decode_error_handler(str(file), E)
        elif fields:
            try:
                json_content = json.loads(fields)
            except json.decoder.JSONDecodeError as E:
                json_decode_error_handler(fields, E)

        obj = self.create(
            title=title,
            name=name,
            description=description,
            json_content=json_content,
            **kwargs,
        )
        print_json(obj)

    def create(
        self,
        title: Optional[str] = None,
        name: Optional[str] = None,
        description: str = "",
        json_content: Optional[Dict] = None,
        **kwargs,
    ) -> Optional[Dict]:
        """Create a new group.

        Args:
            title (Optional[str]): Title of the group.
            name (Optional[str]): Slug/name identifier for the group.
            description (str): Description of the group.
            json_content (Optional[Dict]): Full JSON payload (overrides individual fields).

        Returns:
            Dict: created group details
        """
        if json_content is None:
            if title is None:
                logging.error("missing title for group creation ...")
                sys.exit(1)
            json_content = {
                "title": title,
                "description": description,
            }
            if name is not None:
                json_content["name"] = name

        return self.http_post(
            endpoint=self.ENDPOINT_NAME,
            json=json_content,
        )
