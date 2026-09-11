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

    def __get_map_detail__(self, pk: int, with_blob: bool = True) -> Optional[Dict]:
        """Fetch a map including its MapStore blob and its maplayers.

        GeoNode omits the blob from the default response and exposes it read-only under
        `data` — `blob` itself is write_only on ResourceBaseSerializer, so asking for
        `include[]=blob` silently returns nothing. `maplayers` is not deferred and comes
        along with the detail response, so a single request covers both.

        Args:
            pk (int): pk of the map
            with_blob (bool): request the blob too. Skip it when only the maplayers are
                needed — the blob of a large map is by far the biggest part of the
                response.

        Returns:
            Dict: the map object, or None when it could not be fetched
        """
        params = {"include[]": "data"} if with_blob else {}
        raw = self.http_get(f"{self.ENDPOINT_NAME}/{pk}/", params=params)
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
        # `maplayers` is not deferred, so the blob does not need to be pulled along
        result = self.__get_map_detail__(pk, with_blob=False)
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
    def __is_removed_blob_layer__(
        layer: Dict, msids: set, dataset_pks: set, named_ids: set
    ) -> bool:
        """
        Decide whether a blob layer belongs to one of the maplayers being removed.

        A blob layer is linked to its maplayer by `id` == `extra_params.msId`, which is
        what geonodectl writes and what the MapStore client joins on. Maps that went
        through other tooling also carry layers identified by `extendedParams.pk`, or by
        an `{alternate}__{dataset_pk}` id with neither of the two set.

        The last form is matched in full (`named_ids` holds the exact
        `{alternate}__{dataset_pk}` strings) rather than by a `__{dataset_pk}` suffix:
        `{name}__{index}` is an equally common id shape, so a suffix test would strip an
        unrelated layer whose index happens to equal the dataset pk being removed.

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

        if layer_id is not None and layer_id in named_ids:
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
            return None
        # unwrap the dynamic-rest envelope, like create() does
        return result.get(self.SINGULAR_RESOURCE_NAME, result)

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
        # exact `{alternate}__{dataset_pk}` ids, see __is_removed_blob_layer__
        named_ids = {
            f"{maplayer.get('name')}__{self.__maplayer_dataset_pk__(maplayer)}"
            for maplayer in removed
            if maplayer.get("name")
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
                layer, removed_msids, removed_dataset_pks, named_ids
            )
        ]

        result = self.patch(
            pk=pk, json_content={"data": blob, "maplayers": maplayers_list}
        )
        if result is None:
            logging.error(f"failed to remove maplayers from map {pk}")
            return None
        # unwrap the dynamic-rest envelope, like create() does
        return result.get(self.SINGULAR_RESOURCE_NAME, result)

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

    # MapStore widget types, keyed by the name used on the command line. MapStore's
    # own name for a textbox is "text"; "textbox" reads better as a CLI verb.
    WIDGET_TYPES = {"textbox": "text"}

    # Grid row the first widget of a map is placed in. Row 0 sits flush with the top of
    # the map, where the MapStore toolbars are, so start a little lower down.
    WIDGET_TOP_OFFSET = 2

    @classmethod
    def __next_widget_row__(cls, widgets: List[Dict]) -> int:
        """
        Return the grid row a newly added widget should occupy.

        MapStore lays widgets out with react-grid-layout, so a widget without a free
        row lands on top of an existing one. Stack downwards instead.

        The first widget starts at WIDGET_TOP_OFFSET rather than row 0, which keeps it
        clear of the controls at the top of the map.

        Args:
            widgets (List[Dict]): the widgets already present in the blob

        Returns:
            int: the first free row
        """
        rows: List[int] = [
            row
            for row in ((widget.get("dataGrid") or {}).get("y") for widget in widgets)
            if isinstance(row, int)
        ]
        return max(rows) + 1 if rows else cls.WIDGET_TOP_OFFSET

    @staticmethod
    def __build_text_widget__(
        title: Optional[str], text: Optional[str], row: int
    ) -> Dict:
        """
        Build a MapStore text widget.

        `text` is rendered as HTML by MapStore (TextWidget renders it through the Quill
        `ql-editor`), so markup is passed through untouched.

        Note there is deliberately no `description`: MapStore excludes text widgets from
        the description tool ("text widgets already contain description"), so the key
        would never be shown.

        Args:
            title (str): widget title, shown in the widget header
            text (str): widget body, HTML allowed
            row (int): grid row to place the widget in

        Returns:
            Dict: the widget, ready to be appended to widgetsConfig.widgets
        """
        return {
            "id": str(uuid.uuid4()),
            "widgetType": "text",
            "title": title or "",
            "text": text or "",
            "dataGrid": {"x": 0, "y": row, "w": 1, "h": 1},
        }

    def get_widgets(self, pk: int) -> Optional[List[Dict]]:
        """
        Return the MapStore widgets of a map.

        Args:
            pk (int): pk of the map

        Returns:
            List[Dict]: the widgets, empty when the map has none, None when the blob
                could not be read
        """
        blob = self.get_blob(pk)
        if blob is None:
            # get_blob already reported why
            return None
        return (blob.get("widgetsConfig") or {}).get("widgets") or []

    def add_widget(
        self,
        pk: int,
        widget_type: str = "textbox",
        title: Optional[str] = None,
        text: Optional[str] = None,
        json_path: Optional[str] = None,
        **kwargs,
    ) -> Optional[Dict]:
        """
        Add a widget to the MapStore blob of an existing map.

        Widgets live only in the blob - unlike maplayers there is no parallel API side
        list - so the blob is read, extended and written back as a whole.

        Args:
            pk (int): pk of the map to modify
            widget_type (str): widget type, see WIDGET_TYPES
            title (str): widget title, ignored when json_path is given
            text (str): widget body, HTML allowed, ignored when json_path is given
            json_path (str): path to a JSON file holding a raw widget definition

        Returns:
            Dict: the updated map, or None when nothing was added or the update failed
        """
        if widget_type not in self.WIDGET_TYPES:
            logging.error(
                f"unknown widget type '{widget_type}', "
                f"expected one of: {', '.join(sorted(self.WIDGET_TYPES))}"
            )
            return None

        blob = self.get_blob(pk)
        if blob is None:
            return None

        widgets = blob.setdefault("widgetsConfig", {}).setdefault("widgets", [])
        row = self.__next_widget_row__(widgets)

        if json_path:
            with open(json_path, "r") as f:
                try:
                    widget = json.load(f)
                except json.decoder.JSONDecodeError as e:
                    json_decode_error_handler(json_path, e)
                    return None
            if not isinstance(widget, dict):
                logging.error(f"{json_path} must contain a single JSON object")
                return None
            # a hand written widget may omit the bookkeeping fields
            widget.setdefault("id", str(uuid.uuid4()))
            widget.setdefault("widgetType", self.WIDGET_TYPES[widget_type])
            widget.setdefault("dataGrid", {"x": 0, "y": row, "w": 1, "h": 1})
        else:
            if not title and not text:
                logging.error("either --title or --text is required to add a widget")
                return None
            widget = self.__build_text_widget__(title, text, row)

        widgets.append(widget)

        result = self.patch(pk=pk, json_content={"data": blob})
        if result is None:
            logging.error(f"failed to add widget to map {pk}")
            return None
        # unwrap the dynamic-rest envelope, like create() does
        return result.get(self.SINGULAR_RESOURCE_NAME, result)

    def remove_widget(self, pk: int, widget_id: str, **kwargs) -> Optional[Dict]:
        """
        Remove a widget from the MapStore blob of an existing map.

        Args:
            pk (int): pk of the map to modify
            widget_id (str): id of the widget to remove

        Returns:
            Dict: the updated map, or None when nothing was removed or the update failed
        """
        blob = self.get_blob(pk)
        if blob is None:
            return None

        widgets = (blob.get("widgetsConfig") or {}).get("widgets") or []
        remaining = [widget for widget in widgets if widget.get("id") != widget_id]

        if len(remaining) == len(widgets):
            logging.warning(
                f"map {pk} has no widget with id {widget_id}, doing nothing ... "
            )
            return None

        blob.setdefault("widgetsConfig", {})["widgets"] = remaining

        result = self.patch(pk=pk, json_content={"data": blob})
        if result is None:
            logging.error(f"failed to remove widget {widget_id} from map {pk}")
            return None
        # unwrap the dynamic-rest envelope, like create() does
        return result.get(self.SINGULAR_RESOURCE_NAME, result)

    def cmd_widgets_list(self, pk: int, **kwargs):
        """
        Show the MapStore widgets of a map on the command line.

        Args:
            pk (int): pk of the map

        Example:
          geonodectl maps widgets list 2073
        """
        widgets = self.get_widgets(pk=pk)
        if widgets is None:
            return

        if kwargs.get("json"):
            print_json(widgets)
            return

        show_list(
            headers=["id", "widgetType", "title"],
            values=[
                [
                    str(widget.get("id")),
                    str(widget.get("widgetType")),
                    str(widget.get("title")),
                ]
                for widget in widgets
            ],
        )

    def cmd_widgets_add(
        self,
        pk: int,
        widget_type: str = "textbox",
        title: Optional[str] = None,
        text: Optional[str] = None,
        json_path: Optional[str] = None,
        **kwargs,
    ):
        """
        Add a widget to an existing map.

        Args:
            pk (int): pk of the map to modify
            widget_type (str): widget type, currently only textbox
            title (str): widget title
            text (str): widget body, HTML allowed
            json_path (str): path to a JSON file holding a raw widget definition

        Example:
          geonodectl maps widgets add 2073 textbox --title "test" --text "some text"
        """
        obj = self.add_widget(
            pk=pk,
            widget_type=widget_type,
            title=title,
            text=text,
            json_path=json_path,
            **kwargs,
        )
        if obj is None:
            # add_widget already reported why
            return
        print_json(obj)

    def cmd_widgets_describe(self, pk: int, widget_id: str, **kwargs):
        """
        Show a single widget of a map.

        Args:
            pk (int): pk of the map
            widget_id (str): id of the widget to describe

        Example:
          geonodectl maps widgets describe 2073 3fa85f64-5717-4562-b3fc-2c963f66afa6
        """
        widgets = self.get_widgets(pk=pk)
        if widgets is None:
            return

        for widget in widgets:
            if widget.get("id") == widget_id:
                print_json(widget)
                return
        logging.error(f"map {pk} has no widget with id {widget_id}")

    def cmd_widgets_remove(self, pk: int, widget_id: str, **kwargs):
        """
        Remove a widget from an existing map.

        Args:
            pk (int): pk of the map to modify
            widget_id (str): id of the widget to remove

        Example:
          geonodectl maps widgets remove 2073 3fa85f64-5717-4562-b3fc-2c963f66afa6
        """
        obj = self.remove_widget(pk=pk, widget_id=widget_id, **kwargs)
        if obj is None:
            # remove_widget already reported why
            return
        print_json(obj)
