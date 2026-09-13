import logging
from typing import Dict, List, Optional

from geonoderest.exceptions import GeonodeUsageError, MissingArgumentError
from geonoderest.geonodeobject import GeonodeObjectHandler
from geonoderest.geonodetypes import GeonodeCmdOutListKey
from geonoderest.exitcodes import EXIT_FAILED, EXIT_OK, EXIT_USAGE
from geonoderest.jsonsource import JsonSourceError, load_json_source
from geonoderest.cmdprint import (
    print_json,
)


class GeonodeGroupsHandler(GeonodeObjectHandler):
    ENDPOINT_NAME = "groups"
    JSON_OBJECT_NAME = "group_profiles"
    SINGULAR_RESOURCE_NAME = "group_profile"

    LIST_CMDOUT_HEADER: List[GeonodeCmdOutListKey] = [
        GeonodeCmdOutListKey(key="pk"),
        GeonodeCmdOutListKey(key="title"),
        GeonodeCmdOutListKey(key="slug"),
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
    ) -> int:
        """Create a new group and print the result.

        Args:
            title (Optional[str]): Title of the group.
            name (Optional[str]): Slug/name identifier for the group.
            description (str): Description of the group.
            fields (Optional[str]): JSON string with group data.
            json_path (Optional[str]): Path to a JSON file with group data, or
                a http(s) url serving one.

        Returns:
            int: EXIT_OK, EXIT_FAILED when the API rejected the new group, or
                EXIT_USAGE when the input json or the title was missing
        """
        json_content = None
        if json_path or fields:
            try:
                json_content = load_json_source(json_path=json_path, fields=fields)
            except JsonSourceError as e:
                logging.error(str(e))
                return EXIT_USAGE

        try:
            obj = self.create(
                title=title,
                name=name,
                description=description,
                json_content=json_content,
                **kwargs,
            )
<<<<<<< HEAD
        except GeonodeUsageError as e:
=======
        except ValueError as e:
>>>>>>> 8469f2f77f06012b6e93b29a0598a006cb45aca5
            logging.error(str(e))
            return EXIT_USAGE
        if obj is None:
            logging.error("group creation failed ... ")
            return EXIT_FAILED
        print_json(obj)
        return EXIT_OK

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
                # library method: raise so the caller decides, see #69
<<<<<<< HEAD
                raise MissingArgumentError("missing title for group creation ...")
=======
                raise ValueError("missing title for group creation ...")
>>>>>>> 8469f2f77f06012b6e93b29a0598a006cb45aca5
            json_content = {
                "title": title,
                "slug": name if name is not None else title.lower().replace(" ", "-"),
                "description": description,
            }

        return self.http_post(
            endpoint=self.ENDPOINT_NAME,
            json=json_content,
        )
