from pathlib import Path
import json
from typing import List, Dict, Optional

from geonoderest.cmdprint import print_json, json_decode_error_handler
from geonoderest.resources import GeonodeResourceHandler
from geonoderest.geonodetypes import (
    GeonodeCmdOutListKey,
    GeonodeCmdOutDictKey,
)


class GeonodeMapsHandler(GeonodeResourceHandler):
    ENDPOINT_NAME = JSON_OBJECT_NAME = "maps"
    SINGULAR_RESOURCE_NAME = "map"

    LIST_CMDOUT_HEADER = [
        GeonodeCmdOutListKey(key="pk"),
        GeonodeCmdOutListKey(key="title"),
        GeonodeCmdOutDictKey(key=["owner", "username"]),
        GeonodeCmdOutListKey(key="resource_type"),
        GeonodeCmdOutListKey(key="detail_url"),
    ]

    def cmd_create(
        self,
        title: Path,
        fields: Optional[str] = None,
        json_path: Optional[str] = None,
        **kwargs,
    ):
        """
        creates an (empty) map with the given title and optional maplayers

        Args:
            title (str): title of the new object
            fields (str): string of potential json object
            json_path (str): path to a json file
            maplayers (List[int], optional): list of maplayer pks. Defaults to [].

        Raises:
            Json.decoder.JSONDecodeError: when decoding is not working
        """
        json_content: Dict = {}
        if json_path:
            with open(json_path, "r") as file:
                try:
                    j_dict = json.load(file)
                except json.decoder.JSONDecodeError as E:
                    json_decode_error_handler(str(file), E)

                if "attribute_set" in j_dict:
                    j_dict.pop("attribute_set", None)
            json_content = {**json_content, **j_dict}
        if fields:
            try:
                f_dict = json.loads(fields)
                json_content = {**json_content, **f_dict}
            except json.decoder.JSONDecodeError as E:
                json_decode_error_handler(fields, E)

        obj = self.create(title=title, extra_json_content=json_content, **kwargs)
        print_json(obj)

    def create(
        self,
        title: Path,
        json_content: Optional[Dict] = None,
        maplayers: Optional[List[int]] = [],
        **kwargs,
    ) -> Dict:
        """
        creates an (empty) map with the given title and optional maplayers

        Args:
            title (str): title of the new object
            json_content (dict) dict object with addition metadata / fields
            maplayers (List[int], optional): list of maplayer pks. Defaults to [].

        Raises:
            Json.decoder.JSONDecodeError: when decoding is not working
        """
        maplayers_list = []
        if maplayers is not None:
            maplayers_list = [{"pk": pk} for pk in maplayers]
        base_json_content = {
            "ressource_type": self.SINGULAR_RESOURCE_NAME,
            "title": title,
            "maplayers": maplayers_list,
        }

        json_content = (
            {**base_json_content, **json_content} if json_content else base_json_content
        )
        return self.http_post(
            endpoint=self.ENDPOINT_NAME,
            params=json_content,
        )