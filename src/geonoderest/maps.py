from pathlib import Path
import json
import logging
import uuid

from typing import List, Dict, Optional

from geonoderest.cmdprint import print_json, json_decode_error_handler
from geonoderest.datasets import GeonodeDatasetsHandler
from geonoderest.resources import GeonodeResourceHandler
from geonoderest.geonodetypes import (
    GeonodeCmdOutListKey,
    GeonodeCmdOutDictKey,
)

OGC_WFS_LINK_TYPE = "OGC:WFS"
OGC_WCS_LINK_TYPE = "OGC:WCS"


class GeonodeMapsHandler(GeonodeResourceHandler):
    ENDPOINT_NAME = JSON_OBJECT_NAME = "maps"
    SINGULAR_RESOURCE_NAME = "map"

    LIST_CMDOUT_HEADER = [
        GeonodeCmdOutListKey(key="pk"),
        GeonodeCmdOutListKey(key="title"),
        GeonodeCmdOutDictKey(key=["owner", "username"]),
        GeonodeCmdOutListKey(key="subtype"),
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

    def __build_blob_data__(self):

        # download map template from mapstore config statics of remote geonode instance
        geonode_base_url = self.gn_credentials.get_geonode_base_url()
        blob = self.http_get_download(
            f"{geonode_base_url}/static/mapstore/configs/map.json"
        )

        mapnik_layer = {
            "id": "mapnik__0",
            "name": "mapnik",
            "type": "osm",
            "group": "background",
            "title": "Open Street Map",
            "hidden": False,
            "source": "osm",
            "expanded": False,
            "dimensions": [],
            "singleTile": False,
            "visibility": True,
            "hideLoading": False,
            "useForElevation": False,
            "handleClickOnLayer": False,
        }

        opentopomap_layer = {
            "id": "OpenTopoMap__1",
            "name": "OpenTopoMap",
            "type": "tileprovider",
            "group": "background",
            "title": "OpenTopoMap",
            "hidden": False,
            "source": "OpenTopoMap",
            "expanded": False,
            "provider": "OpenTopoMap",
            "dimensions": [],
            "singleTile": False,
            "visibility": False,
            "hideLoading": False,
            "useForElevation": False,
            "handleClickOnLayer": False,
        }

        s2cloudless_layer = {
            "id": "s2cloudless",
            "url": "https://maps.geosolutionsgroup.com/geoserver/wms",
            "name": "s2cloudless:s2cloudless",
            "type": "wms",
            "group": "background",
            "title": "Sentinel-2 cloudless - https://s2maps.eu",
            "format": "image/jpeg",
            "hidden": False,
            "expanded": False,
            "thumbURL": "{geonode_base_url}/static/mapstorestyle/img/s2cloudless-s2cloudless.png",
            "dimensions": [],
            "singleTile": False,
            "visibility": False,
            "hideLoading": False,
            "useForElevation": False,
            "handleClickOnLayer": False,
        }

        none_layer = {
            "id": "none",
            "name": "empty",
            "type": "empty",
            "group": "background",
            "title": "Empty Background",
            "hidden": False,
            "source": "ol",
            "expanded": False,
            "dimensions": [],
            "singleTile": False,
            "visibility": False,
            "hideLoading": False,
            "useForElevation": False,
            "handleClickOnLayer": False,
        }
        blob["map"]["layers"].append(mapnik_layer)
        blob["map"]["layers"].append(opentopomap_layer)
        blob["map"]["layers"].append(s2cloudless_layer)
        blob["map"]["layers"].append(none_layer)

        return blob

    def __build_blob_maplayer__(
        self, maplayer_uuid: str, ds_title: str, alternate: str, dataset: Dict
    ):
        """
        Builds a blob layer with provided map layer UUID, dataset title, name, and dataset information.

        Args:
            maplayer_uuid (str): Unique identifier for the map layer.
            ds_title (str): Title of the dataset.
            name (str): Style name for the map layer.
            dataset (Dict): Dataset information containing links, extent, and other metadata.

        Returns:
            dict: A dictionary representing the blob layer with attributes such as id, url, bbox,
                  name, type, style, title, feature info template, and additional configurations.
        """

        for link in dataset["links"]:
            if link["link_type"] == OGC_WFS_LINK_TYPE:
                wfs_url = link["url"]
            if link["link_type"] == OGC_WCS_LINK_TYPE:
                wfs_url = link["url"]

        ptype = "wms" if dataset["ptype"] == "gxp_wmscsource" else "wfs"

        blob_layer = {
            "id": maplayer_uuid,
            "url": wfs_url,
            "bbox": {
                "crs": dataset["extent"]["srid"],
                "bounds": {
                    "maxx": dataset["extent"]["coords"][2],
                    "maxy": dataset["extent"]["coords"][3],
                    "minx": dataset["extent"]["coords"][0],
                    "miny": dataset["extent"]["coords"][1],
                },
            },
            "name": alternate,
            "type": ptype,
            "style": alternate,
            "title": ds_title,
            "hidden": False,
            "search": {"url": wfs_url, "type": "wfs"},
            "expanded": False,
            "dimensions": [],
            "singleTile": False,
            "visibility": True,
            "featureInfo": {
                "format": "TEMPLATE",
                "template": '<div style="overflow-x:hidden"><div class="row"><div class="col-xs-6" style="font-weight: bold; word-wrap: break-word;">SITE_ID:</div>                             <div class="col-xs-6" style="word-wrap: break-word;">${properties[\'SITE_ID\']}</div></div><div class="row"><div class="col-xs-6" style="font-weight: bold; word-wrap: break-word;">STAT_NUM:</div>                             <div class="col-xs-6" style="word-wrap: break-word;">${properties[\'STAT_NUM\']}</div></div><div class="row"><div class="col-xs-6" style="font-weight: bold; word-wrap: break-word;">NAME:</div>                             <div class="col-xs-6" style="word-wrap: break-word;">${properties[\'NAME\']}</div></div><div class="row"><div class="col-xs-6" style="font-weight: bold; word-wrap: break-word;">FAO_SOIL:</div>                             <div class="col-xs-6" style="word-wrap: break-word;">${properties[\'FAO_SOIL\']}</div></div><div class="row"><div class="col-xs-6" style="font-weight: bold; word-wrap: break-word;">COUNTRY:</div>                             <div class="col-xs-6" style="word-wrap: break-word;">${properties[\'COUNTRY\']}</div></div><div class="row"><div class="col-xs-6" style="font-weight: bold; word-wrap: break-word;">LOCALMSSG:</div>                             <div class="col-xs-6" style="word-wrap: break-word;">${properties[\'LOCALMSSG\']}</div></div><div class="row"><div class="col-xs-6" style="font-weight: bold; word-wrap: break-word;">TOP_DEPTH_GW:</div>                             <div class="col-xs-6" style="word-wrap: break-word;">${properties[\'TOP_DEPTH_GW\']}</div></div><div class="row"><div class="col-xs-6" style="font-weight: bold; word-wrap: break-word;">BOT_DEPTH_GW:</div>                             <div class="col-xs-6" style="word-wrap: break-word;">${properties[\'BOT_DEPTH_GW\']}</div></div><div class="row"><div class="col-xs-6" style="font-weight: bold; word-wrap: break-word;">SITEDESCRIP:</div>                             <div class="col-xs-6" style="word-wrap: break-word;">${properties[\'SITEDESCRIP\']}</div></div><div class="row"><div class="col-xs-6" style="font-weight: bold; word-wrap: break-word;">SAMPLEDATE:</div>                             <div class="col-xs-6" style="word-wrap: break-word;">${properties[\'SAMPLEDATE\']}</div></div><div class="row"><div class="col-xs-6" style="font-weight: bold; word-wrap: break-word;">ANNRAIN:</div>                             <div class="col-xs-6" style="word-wrap: break-word;">${properties[\'ANNRAIN\']}</div></div><div class="row"><div class="col-xs-6" style="font-weight: bold; word-wrap: break-word;">AVE_JAN_TEMP:</div>                             <div class="col-xs-6" style="word-wrap: break-word;">${properties[\'AVE_JAN_TEMP\']}</div></div><div class="row"><div class="col-xs-6" style="font-weight: bold; word-wrap: break-word;">AVE_JUL_TEMP:</div>                             <div class="col-xs-6" style="word-wrap: break-word;">${properties[\'AVE_JUL_TEMP\']}</div></div><div class="row"><div class="col-xs-6" style="font-weight: bold; word-wrap: break-word;">NUMBER_HOR:</div>                             <div class="col-xs-6" style="word-wrap: break-word;">${properties[\'NUMBER_HOR\']}</div></div><div class="row"><div class="col-xs-6" style="font-weight: bold; word-wrap: break-word;">X_ETRS89:</div>                             <div class="col-xs-6" style="word-wrap: break-word;">${properties[\'X_ETRS89\']}</div></div><div class="row"><div class="col-xs-6" style="font-weight: bold; word-wrap: break-word;">Y_ETRS89:</div>                             <div class="col-xs-6" style="word-wrap: break-word;">${properties[\'Y_ETRS89\']}</div></div><div class="row"><div class="col-xs-6" style="font-weight: bold; word-wrap: break-word;">ZONE:</div>                             <div class="col-xs-6" style="word-wrap: break-word;">${properties[\'ZONE\']}</div></div></div>',
            },
            "hideLoading": False,
            "extendedParams": {
                "pk": dataset["pk"],
                "mapLayer": {
                    "dataset": dataset,
                    "defaultStyle": {"name": alternate, "title": alternate},
                },
            },
            "useForElevation": False,
            "handleClickOnLayer": False,
        }
        return blob_layer

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
        # initialize Dataset Handler, required for map.blob.layer and api.map.maplayer building
        gnDatasetsHandler = GeonodeDatasetsHandler(self.gn_credentials)

        # init map blob
        blob = self.__build_blob_data__()

        # init maplayer list
        maplayers_list = []
        order: int = 0

        if maplayers is not None:
            for maplayer_pk in maplayers:

                # get dataset of maplayer pk
                dataset = gnDatasetsHandler.get(pk=maplayer_pk)

                # uuid to connect blob layer with api.maplayer
                maplayer_uuid = str(uuid.uuid4())

                # append map.blob.layer to blob data
                blob["map"]["layers"].append(
                    self.__build_blob_maplayer__(
                        maplayer_uuid, dataset["title"], dataset["alternate"], dataset
                    )
                )

                # build new api.map.maplayer
                maplayers_list.append(
                    {
                        "extra_params": {"msId": maplayer_uuid, "styles": []},
                        "current_style": dataset["alternate"],
                        # "dataset": dataset,
                        "name": dataset["alternate"],
                        "order": order,
                        "visibility": True,
                        "opacity": 1.0,
                    }
                )
                order += 1

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
            json=json_content,
        )
        if r is None:
            return None
        return r[self.SINGULAR_RESOURCE_NAME]
