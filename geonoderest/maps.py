from pathlib import Path
import json
import logging
from typing import List, Dict, Optional

from geonoderest.cmdprint import print_json, json_decode_error_handler
from geonoderest.datasets import GeonodeDatasetsHandler
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
        maplayers: Optional[List[int]] = [],
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
            title=title, json_content=json_content, maplayers=maplayers, **kwargs
        )
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

        # download map template from mapstore config statics of remote geonode instance
        geonode_base_url = self.gn_credentials.get_geonode_base_url()
        blob = self.http_get_download(
            f"{geonode_base_url}/static/mapstore/configs/map.json"
        )

        # add maplayers to map.blob
        gnResourceHandler = GeonodeResourceHandler(self.gn_credentials)
        if maplayers is not None:
            for maplayer_pk in maplayers:
                try:
                    blob["map"]["layers"].append(gnResourceHandler.get(pk=maplayer_pk))
                except Exception as err:
                    logging.error(f"dataset {maplayer_pk} not found ...")

        base_json_content = {
            "ressource_type": self.SINGULAR_RESOURCE_NAME,
            "title": title,
            "blob": blob,
            "maplayers": maplayers_list,
        }

        json_content = (
            {**base_json_content, **json_content} if json_content else base_json_content
        )
        r = self.http_post(
            endpoint=self.ENDPOINT_NAME,
            params=json_content,
        )
        return r[self.SINGULAR_RESOURCE_NAME]
