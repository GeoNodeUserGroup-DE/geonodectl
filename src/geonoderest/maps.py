from pathlib import Path
import json
import logging
import uuid

from typing import List, Dict, Optional, Tuple

from geonoderest.cmdprint import print_json, json_decode_error_handler, show_list
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
        blob = blob.json()

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
        self,
        maplayer_uuid: str,
        ds_title: str,
        alternate: str,
        dataset: Dict,
        hidden: bool = True,
        visibility: bool = True,
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

        # datasets without an OGC:WFS/OGC:WCS link (rasters, remote services) fall back
        # to the dataset ows_url, otherwise the layer would be built with no url at all
        wfs_url: Optional[str] = dataset.get("ows_url")
        for link in dataset.get("links", []):
            if link["link_type"] == OGC_WFS_LINK_TYPE:
                wfs_url = link["url"]
            if link["link_type"] == OGC_WCS_LINK_TYPE:
                wfs_url = link["url"]

        ptype = "wms" if dataset["ptype"] == "gxp_wmscsource" else "wfs"

        blob_layer: Dict = {
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
            "hidden": hidden,
            "search": {"url": wfs_url, "type": "wfs"},
            "expanded": False,
            "dimensions": [],
            "singleTile": False,
            "visibility": visibility,
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

    def __build_maplayer_pair__(self, dataset: Dict, order: int) -> Tuple[Dict, Dict]:
        """
        Builds the two representations a maplayer needs: the MapStore blob layer and the
        api.map.maplayer entry. Both are linked by a freshly generated msId uuid.

        Args:
            dataset (Dict): dataset object as returned by the datasets endpoint
            order (int): position of the layer within the map

        Returns:
            Tuple[Dict, Dict]: (blob layer, maplayer entry)
        """
        # uuid to connect blob layer with api.maplayer
        maplayer_uuid = str(uuid.uuid4())

        hidden = True
        visibility = True
        if dataset["subtype"] == "tabular":
            visibility = False
            hidden = False

        blob_layer = self.__build_blob_maplayer__(
            maplayer_uuid,
            dataset["title"],
            dataset["alternate"],
            dataset,
            hidden=hidden,
            visibility=visibility,
        )

        maplayer = {
            "extra_params": {"msId": maplayer_uuid, "styles": []},
            "current_style": dataset["alternate"],
            # "dataset": dataset,
            "name": dataset["alternate"],
            "order": order,
            "visibility": visibility,
            "opacity": 1.0,
        }

        return blob_layer, maplayer

    def create(
        self,
        title: Path,
        json_content: Optional[Dict] = None,
        maplayers: Optional[List[int]] = [],
        **kwargs,
    ) -> Optional[Dict]:
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

                blob_layer, maplayer = self.__build_maplayer_pair__(dataset, order)

                # append map.blob.layer to blob data
                blob["map"]["layers"].append(blob_layer)

                # build new api.map.maplayer
                maplayers_list.append(maplayer)
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

    def __get_map_detail__(self, pk: int) -> Optional[Dict]:
        """Fetch a map including its MapStore blob and its maplayers.

        GeoNode omits the blob from the default response and exposes it read-only under
        `data` — `blob` itself is write_only on ResourceBaseSerializer, so asking for
        `include[]=blob` silently returns nothing. `maplayers` is not deferred and comes
        along with the detail response, so a single request covers both.

        Args:
            pk (int): pk of the map

        Returns:
            Dict: the map object, or None when it could not be fetched
        """
        raw = self.http_get(f"{self.ENDPOINT_NAME}/{pk}/", params={"include[]": "data"})
        if raw is None:
            logging.error(f"Map {pk} not found")
            return None
        result = raw.get(self.SINGULAR_RESOURCE_NAME)
        if result is None:
            logging.error(f"Map {pk} not found")
            return None
        return result

    def get_blob(self, pk: int) -> Optional[Dict]:
        """Return the MapStore blob JSON of a map.

        Args:
            pk (int): pk of the map

        Returns:
            Dict: the blob, or None when the map has none
        """
        result = self.__get_map_detail__(pk)
        if result is None:
            return None
        # `blob` fallback for deployments that expose it read-write
        blob = result.get("data") or result.get("blob")
        if not blob:
            logging.error(
                f"Map {pk} has no blob — the map may not have been configured yet"
            )
            return None
        return blob

    def get_maplayers(self, pk: int) -> Optional[List[Dict]]:
        """Return the maplayers of a map.

        Args:
            pk (int): pk of the map

        Returns:
            List[Dict]: the maplayers as returned by the maps detail endpoint
        """
        result = self.__get_map_detail__(pk)
        if result is None:
            return None
        return result.get("maplayers", [])

    def cmd_get_blob(self, pk: int, **kwargs):
        """Print the MapStore blob JSON for a map to stdout.

        Useful for inspection and shell pipelines:
          geonodectl maps get-blob 2073 | jq '.map.layers'
        """
        blob = self.get_blob(pk=pk)
        if blob is None:
            return
        print_json(blob)

    def cmd_set_blob(self, pk: int, json_path: Optional[str] = None, **kwargs):
        """Replace the MapStore blob JSON for a map from a JSON file.

        Args:
            pk (int): pk of the map to update
            json_path (str): path to a JSON file containing the new blob

        Example:
          geonodectl maps set-blob 2073 --json_path ./blob.json
        """
        if not json_path:
            raise ValueError("--json_path is required for set-blob")
        with open(json_path, "r") as f:
            try:
                blob = json.load(f)
            except json.decoder.JSONDecodeError as e:
                json_decode_error_handler(json_path, e)
                return
        result = self.patch(pk=pk, json_content={"blob": blob})
        if result is None:
            logging.error(f"Failed to update blob for map {pk}")
            return
        print_json(result)

    @staticmethod
    def __maplayer_dataset_pk__(maplayer: Dict) -> Optional[int]:
        """pk of the dataset a maplayer points to, None if it is not resolved"""
        return (maplayer.get("dataset") or {}).get("pk")

    @staticmethod
    def __minimal_maplayer__(maplayer: Dict, order: int) -> Dict:
        """
        Reduce a maplayer as returned by the API to the fields that can be written back.

        The embedded `dataset` is dropped on purpose: GeoNode resolves MapLayer.dataset
        from `name` (the dataset alternate) in a pre_save signal, and sending the whole
        embedded dataset back would have to pass the full dataset serializer. `pk` is
        kept so GeoNode updates the existing row instead of recreating it.

        Args:
            maplayer (Dict): maplayer as returned by the maps detail endpoint
            order (int): position to write into the maplayer

        Returns:
            Dict: maplayer reduced to its writable fields
        """
        minimal = {
            "pk": maplayer.get("pk"),
            "extra_params": maplayer.get("extra_params") or {},
            "current_style": maplayer.get("current_style"),
            "name": maplayer.get("name"),
            "order": order,
            "visibility": maplayer.get("visibility", True),
            "opacity": maplayer.get("opacity", 1.0),
        }
        return minimal

    @staticmethod
    def __sorted_maplayers__(maplayers: List[Dict]) -> List[Dict]:
        """
        Sort maplayers by their stored order.

        The API returns maplayers newest first (MapLayer.Meta.ordering is ["-pk"]), so
        renumbering them in the order they arrive would scramble the layer stack of the
        map on every add or remove.
        """
        return sorted(maplayers, key=lambda maplayer: maplayer.get("order") or 0)

    @staticmethod
    def __is_removed_blob_layer__(layer: Dict, msids: set, dataset_pks: set) -> bool:
        """
        Decide whether a blob layer belongs to one of the maplayers being removed.

        A blob layer is linked to its maplayer by `id` == `extra_params.msId`, but maps
        edited in MapStore also carry layers identified by `extendedParams.pk` or by an
        `{alternate}__{dataset_pk}` id, so all three are matched.

        Background layers are never removed — they are not maplayers at all.
        """
        if layer.get("group") == "background":
            return False

        layer_id = layer.get("id")
        if layer_id is not None and layer_id in msids:
            return True

        extended_pk = (layer.get("extendedParams") or {}).get("pk")
        if extended_pk is not None and extended_pk in dataset_pks:
            return True

        if isinstance(layer_id, str) and any(
            layer_id.endswith(f"__{dataset_pk}") for dataset_pk in dataset_pks
        ):
            return True

        return False

    def add_maplayers(self, pk: int, datasets: List[int], **kwargs) -> Optional[Dict]:
        """
        Add datasets as maplayers to an existing map.

        The maps API replaces the whole maplayers list on PATCH — every maplayer missing
        from the payload is deleted — so the current list is read, extended and written
        back as a whole, together with the matching MapStore blob layers.

        Args:
            pk (int): pk of the map to modify
            datasets (List[int]): list of dataset pks to add

        Returns:
            Dict: the updated map, or None when nothing was added or the update failed
        """
        detail = self.__get_map_detail__(pk)
        if detail is None:
            return None

        blob = detail.get("data") or detail.get("blob")
        if not blob:
            logging.error(
                f"Map {pk} has no blob — the map may not have been configured yet"
            )
            return None

        maplayers = self.__sorted_maplayers__(detail.get("maplayers") or [])
        existing_dataset_pks = {
            self.__maplayer_dataset_pk__(maplayer) for maplayer in maplayers
        }

        order = 0
        maplayers_list = []
        for maplayer in maplayers:
            maplayers_list.append(self.__minimal_maplayer__(maplayer, order))
            order += 1

        blob_layers = blob.setdefault("map", {}).setdefault("layers", [])
        gnDatasetsHandler = GeonodeDatasetsHandler(self.gn_credentials)

        added = 0
        for dataset_pk in datasets:
            if dataset_pk in existing_dataset_pks:
                logging.warning(
                    f"dataset {dataset_pk} is already a maplayer of map {pk}, skipping ... "
                )
                continue

            dataset = gnDatasetsHandler.get(pk=dataset_pk)
            if dataset is None:
                logging.error(f"dataset {dataset_pk} not found, skipping ... ")
                continue

            blob_layer, maplayer = self.__build_maplayer_pair__(dataset, order)
            blob_layers.append(blob_layer)
            maplayers_list.append(maplayer)
            existing_dataset_pks.add(dataset_pk)
            order += 1
            added += 1

        if added == 0:
            logging.warning(f"nothing to add to map {pk}, doing nothing ... ")
            return None

        result = self.patch(
            pk=pk, json_content={"data": blob, "maplayers": maplayers_list}
        )
        if result is None:
            logging.error(f"failed to add maplayers to map {pk}")
        return result

    def remove_maplayers(
        self, pk: int, datasets: List[int], **kwargs
    ) -> Optional[Dict]:
        """
        Remove the maplayers pointing to the given datasets from an existing map.

        Removes both the api.map.maplayer entries and the matching MapStore blob layers,
        then renumbers the order of the remaining maplayers.

        Args:
            pk (int): pk of the map to modify
            datasets (List[int]): list of dataset pks to remove

        Returns:
            Dict: the updated map, or None when nothing was removed or the update failed
        """
        detail = self.__get_map_detail__(pk)
        if detail is None:
            return None

        blob = detail.get("data") or detail.get("blob")
        if not blob:
            logging.error(
                f"Map {pk} has no blob — the map may not have been configured yet"
            )
            return None

        maplayers = self.__sorted_maplayers__(detail.get("maplayers") or [])
        requested = set(datasets)

        removed = [
            maplayer
            for maplayer in maplayers
            if self.__maplayer_dataset_pk__(maplayer) in requested
        ]
        if len(removed) == 0:
            logging.warning(
                f"none of the datasets {sorted(requested)} is a maplayer of map {pk}, "
                "doing nothing ... "
            )
            return None

        not_found = requested - {
            self.__maplayer_dataset_pk__(maplayer) for maplayer in removed
        }
        for dataset_pk in sorted(not_found):
            logging.warning(
                f"dataset {dataset_pk} is not a maplayer of map {pk}, skipping ... "
            )

        removed_msids = {
            (maplayer.get("extra_params") or {}).get("msId") for maplayer in removed
        }
        removed_msids.discard(None)
        removed_dataset_pks = {
            self.__maplayer_dataset_pk__(maplayer) for maplayer in removed
        }

        order = 0
        maplayers_list = []
        for maplayer in maplayers:
            if self.__maplayer_dataset_pk__(maplayer) in requested:
                continue
            maplayers_list.append(self.__minimal_maplayer__(maplayer, order))
            order += 1

        blob.setdefault("map", {})["layers"] = [
            layer
            for layer in blob.get("map", {}).get("layers", [])
            if not self.__is_removed_blob_layer__(
                layer, removed_msids, removed_dataset_pks
            )
        ]

        result = self.patch(
            pk=pk, json_content={"data": blob, "maplayers": maplayers_list}
        )
        if result is None:
            logging.error(f"failed to remove maplayers from map {pk}")
        return result

    def cmd_maplayers_list(self, pk: int, **kwargs):
        """
        Show the maplayers of a map on the command line.

        Args:
            pk (int): pk of the map
        """
        maplayers = self.get_maplayers(pk=pk)
        if maplayers is None:
            return

        if kwargs.get("json"):
            print_json(maplayers)
            return

        maplayers = self.__sorted_maplayers__(maplayers)
        show_list(
            headers=[
                "dataset.pk",
                "name",
                "current_style",
                "order",
                "visibility",
                "opacity",
            ],
            values=[
                [
                    str(self.__maplayer_dataset_pk__(maplayer)),
                    str(maplayer.get("name")),
                    str(maplayer.get("current_style")),
                    str(maplayer.get("order")),
                    str(maplayer.get("visibility")),
                    str(maplayer.get("opacity")),
                ]
                for maplayer in maplayers
            ],
        )

    def cmd_maplayers_add(self, pk: int, datasets: List[int] = [], **kwargs):
        """
        Add datasets as maplayers to an existing map.

        Args:
            pk (int): pk of the map to modify
            datasets (List[int]): list of dataset pks to add

        Example:
          geonodectl maps maplayers add 2073 36 42
        """
        if len(datasets) == 0:
            logging.warning("no datasets given to add, doing nothing ... ")
            return
        obj = self.add_maplayers(pk=pk, datasets=datasets, **kwargs)
        if obj is None:
            # add_maplayers already reported why
            return
        print_json(obj)

    def cmd_maplayers_remove(self, pk: int, datasets: List[int] = [], **kwargs):
        """
        Remove the maplayers pointing to the given datasets from an existing map.

        Args:
            pk (int): pk of the map to modify
            datasets (List[int]): list of dataset pks to remove

        Example:
          geonodectl maps maplayers remove 2073 36
        """
        if len(datasets) == 0:
            logging.warning("no datasets given to remove, doing nothing ... ")
            return
        obj = self.remove_maplayers(pk=pk, datasets=datasets, **kwargs)
        if obj is None:
            # remove_maplayers already reported why
            return
        print_json(obj)
