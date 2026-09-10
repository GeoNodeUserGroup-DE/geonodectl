import json
import tempfile
import unittest
from unittest.mock import call, patch

from geonoderest.maps import GeonodeMapsHandler

BLOB = {
    "version": 2,
    "map": {"projection": "EPSG:3857", "layers": []},
    "maplayers": [],
}


class TestGeonodeMapsHandler(unittest.TestCase):
    @patch.object(GeonodeMapsHandler, "http_get")
    def test_get(self, mock_http_get):
        mock_http_get.return_value = {"map": {"pk": 1, "title": "Test Map"}}
        handler = GeonodeMapsHandler(env={})
        result = handler.get(123)
        self.assertEqual(result["title"], "Test Map")

    @patch.object(GeonodeMapsHandler, "http_patch")
    def test_patch(self, mock_http_patch):
        mock_http_patch.return_value = {"success": True}
        handler = GeonodeMapsHandler(env={})
        result = handler.patch(123, json_content={"title": "Updated"})
        self.assertTrue(result["success"])

    @patch.object(GeonodeMapsHandler, "http_delete")
    def test_delete_uses_resources_endpoint(self, mock_http_delete):
        """maps API does not allow DELETE — delete must use resources/{pk}/delete."""
        mock_http_delete.return_value = {}
        handler = GeonodeMapsHandler(env={})
        handler.delete(pk=5)
        mock_http_delete.assert_called_once_with(endpoint="resources/5/delete")


class TestCmdGetBlob(unittest.TestCase):
    def _handler(self):
        return GeonodeMapsHandler(env={})

    @patch.object(GeonodeMapsHandler, "http_get")
    def test_requests_blob_with_include_data_param(self, mock_http_get):
        """`blob` is write_only server side, the readable representation is `data`."""
        mock_http_get.return_value = {"map": {"pk": 42, "data": BLOB}}
        with patch("geonoderest.maps.print_json"):
            self._handler().cmd_get_blob(pk=42)
        mock_http_get.assert_called_once_with("maps/42/", params={"include[]": "data"})

    @patch.object(GeonodeMapsHandler, "http_get")
    def test_prints_blob(self, mock_http_get):
        mock_http_get.return_value = {"map": {"pk": 42, "data": BLOB}}
        with patch("geonoderest.maps.print_json") as mock_print:
            self._handler().cmd_get_blob(pk=42)
        mock_print.assert_called_once_with(BLOB)

    @patch.object(GeonodeMapsHandler, "http_get")
    def test_falls_back_to_blob_key(self, mock_http_get):
        """deployments exposing `blob` read-write are still supported"""
        mock_http_get.return_value = {"map": {"pk": 42, "blob": BLOB}}
        with patch("geonoderest.maps.print_json") as mock_print:
            self._handler().cmd_get_blob(pk=42)
        mock_print.assert_called_once_with(BLOB)

    @patch.object(GeonodeMapsHandler, "http_get", return_value=None)
    def test_logs_error_when_map_not_found(self, _):
        with self.assertLogs(level="ERROR"):
            self._handler().cmd_get_blob(pk=999)

    @patch.object(GeonodeMapsHandler, "http_get")
    def test_logs_error_when_blob_is_empty(self, mock_http_get):
        mock_http_get.return_value = {"map": {"pk": 42, "data": {}}}
        with self.assertLogs(level="ERROR"):
            self._handler().cmd_get_blob(pk=42)

    @patch.object(GeonodeMapsHandler, "http_get")
    def test_logs_error_when_blob_is_absent(self, mock_http_get):
        mock_http_get.return_value = {"map": {"pk": 42}}
        with self.assertLogs(level="ERROR"):
            self._handler().cmd_get_blob(pk=42)


class TestCmdSetBlob(unittest.TestCase):
    def _handler(self):
        return GeonodeMapsHandler(env={})

    @patch.object(GeonodeMapsHandler, "http_patch")
    def test_patches_map_with_blob_from_file(self, mock_patch):
        mock_patch.return_value = {"map": {"pk": 42}}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(BLOB, f)
            path = f.name
        with patch("geonoderest.maps.print_json"):
            self._handler().cmd_set_blob(pk=42, json_path=path)
        args, kwargs = mock_patch.call_args
        self.assertEqual(kwargs["json_content"]["blob"], BLOB)

    @patch.object(GeonodeMapsHandler, "http_patch")
    def test_prints_result_on_success(self, mock_patch):
        mock_patch.return_value = {"map": {"pk": 42, "title": "T"}}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(BLOB, f)
            path = f.name
        with patch("geonoderest.maps.print_json") as mock_print:
            self._handler().cmd_set_blob(pk=42, json_path=path)
        mock_print.assert_called_once()

    @patch.object(GeonodeMapsHandler, "http_patch", return_value=None)
    def test_logs_error_when_patch_fails(self, _):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(BLOB, f)
            path = f.name
        with self.assertLogs(level="ERROR"):
            self._handler().cmd_set_blob(pk=42, json_path=path)

    def test_raises_when_no_json_path(self):
        with self.assertRaises(ValueError):
            self._handler().cmd_set_blob(pk=42, json_path=None)


def _background_layer(layer_id):
    return {"id": layer_id, "group": "background", "name": layer_id}


def _dataset_layer(layer_id, dataset_pk):
    return {
        "id": layer_id,
        "name": f"geonode:ds{dataset_pk}",
        "extendedParams": {"pk": dataset_pk},
    }


def _maplayer(pk, dataset_pk, msid, order):
    return {
        "pk": pk,
        "extra_params": {"msId": msid, "styles": []},
        "current_style": f"geonode:ds{dataset_pk}",
        # the API embeds the whole dataset here, it must not be written back
        "dataset": {"pk": dataset_pk, "alternate": f"geonode:ds{dataset_pk}"},
        "name": f"geonode:ds{dataset_pk}",
        "order": order,
        "visibility": True,
        "opacity": 1.0,
    }


def _map_detail():
    """a map with two background layers and two dataset maplayers (pks 101, 102)"""
    return {
        "map": {
            "pk": 42,
            "data": {
                "version": 2,
                "map": {
                    "projection": "EPSG:3857",
                    "layers": [
                        _background_layer("mapnik__0"),
                        _background_layer("none"),
                        _dataset_layer("msid-101", 101),
                        _dataset_layer("msid-102", 102),
                    ],
                },
            },
            # the API returns maplayers newest first (MapLayer.Meta.ordering is ["-pk"]),
            # so the arrival order deliberately disagrees with the stored `order`
            "maplayers": [
                _maplayer(902, 102, "msid-102", 1),
                _maplayer(901, 101, "msid-101", 0),
            ],
        }
    }


def _dataset(pk):
    return {
        "pk": pk,
        "title": f"Dataset {pk}",
        "alternate": f"geonode:ds{pk}",
        "subtype": "vector",
        "ptype": "gxp_wmscsource",
        "ows_url": "https://example.org/geoserver/ows",
        "links": [{"link_type": "OGC:WFS", "url": "https://example.org/geoserver/wfs"}],
        "extent": {"srid": "EPSG:4326", "coords": [0, 0, 1, 1]},
    }


class TestAddMaplayers(unittest.TestCase):
    def _handler(self):
        return GeonodeMapsHandler(env={})

    def _add(self, mock_http_get, mock_patch, datasets, existing=(101, 102)):
        mock_http_get.return_value = _map_detail()
        mock_patch.return_value = {"pk": 42}
        with patch("geonoderest.maps.GeonodeDatasetsHandler") as mock_ds_handler:
            mock_ds_handler.return_value.get.side_effect = lambda pk: _dataset(pk)
            result = self._handler().add_maplayers(pk=42, datasets=datasets)
        return result

    @patch.object(GeonodeMapsHandler, "patch")
    @patch.object(GeonodeMapsHandler, "http_get")
    def test_keeps_pk_of_existing_maplayers(self, mock_http_get, mock_patch):
        """the maps API deletes every maplayer missing from the payload"""
        self._add(mock_http_get, mock_patch, [103])
        maplayers = mock_patch.call_args.kwargs["json_content"]["maplayers"]
        self.assertEqual([m["pk"] for m in maplayers[:2]], [901, 902])
        # the new entry carries no pk, so GeoNode creates a row instead of updating one
        self.assertNotIn("pk", maplayers[2])

    @patch.object(GeonodeMapsHandler, "patch")
    @patch.object(GeonodeMapsHandler, "http_get")
    def test_does_not_write_back_embedded_dataset(self, mock_http_get, mock_patch):
        self._add(mock_http_get, mock_patch, [103])
        maplayers = mock_patch.call_args.kwargs["json_content"]["maplayers"]
        for maplayer in maplayers:
            self.assertNotIn("dataset", maplayer)

    @patch.object(GeonodeMapsHandler, "patch")
    @patch.object(GeonodeMapsHandler, "http_get")
    def test_appends_one_maplayer_and_one_blob_layer(self, mock_http_get, mock_patch):
        self._add(mock_http_get, mock_patch, [103])
        json_content = mock_patch.call_args.kwargs["json_content"]
        self.assertEqual(len(json_content["maplayers"]), 3)
        self.assertEqual(len(json_content["data"]["map"]["layers"]), 5)

    @patch.object(GeonodeMapsHandler, "patch")
    @patch.object(GeonodeMapsHandler, "http_get")
    def test_blob_layer_id_matches_new_msid(self, mock_http_get, mock_patch):
        """the blob layer and the maplayer are joined by msId == blob layer id"""
        self._add(mock_http_get, mock_patch, [103])
        json_content = mock_patch.call_args.kwargs["json_content"]
        new_maplayer = json_content["maplayers"][-1]
        new_blob_layer = json_content["data"]["map"]["layers"][-1]
        self.assertEqual(new_maplayer["extra_params"]["msId"], new_blob_layer["id"])
        self.assertEqual(new_blob_layer["extendedParams"]["pk"], 103)

    @patch.object(GeonodeMapsHandler, "patch")
    @patch.object(GeonodeMapsHandler, "http_get")
    def test_order_continues_from_existing(self, mock_http_get, mock_patch):
        self._add(mock_http_get, mock_patch, [103, 104])
        maplayers = mock_patch.call_args.kwargs["json_content"]["maplayers"]
        self.assertEqual([m["order"] for m in maplayers], [0, 1, 2, 3])

    @patch.object(GeonodeMapsHandler, "patch")
    @patch.object(GeonodeMapsHandler, "http_get")
    def test_does_not_scramble_existing_layer_stack(self, mock_http_get, mock_patch):
        """the API returns maplayers newest first — renumbering must follow `order`"""
        self._add(mock_http_get, mock_patch, [103])
        maplayers = mock_patch.call_args.kwargs["json_content"]["maplayers"]
        self.assertEqual([m["pk"] for m in maplayers[:2]], [901, 902])

    @patch.object(GeonodeMapsHandler, "patch")
    @patch.object(GeonodeMapsHandler, "http_get")
    def test_already_present_dataset_is_skipped(self, mock_http_get, mock_patch):
        with self.assertLogs(level="WARNING"):
            result = self._add(mock_http_get, mock_patch, [101])
        self.assertIsNone(result)
        mock_patch.assert_not_called()

    @patch.object(GeonodeMapsHandler, "patch")
    @patch.object(GeonodeMapsHandler, "http_get")
    def test_partially_present_still_adds_the_rest(self, mock_http_get, mock_patch):
        with self.assertLogs(level="WARNING"):
            self._add(mock_http_get, mock_patch, [101, 103])
        maplayers = mock_patch.call_args.kwargs["json_content"]["maplayers"]
        self.assertEqual(len(maplayers), 3)

    @patch.object(GeonodeMapsHandler, "http_get", return_value=None)
    def test_returns_none_when_map_not_found(self, _):
        with self.assertLogs(level="ERROR"):
            self.assertIsNone(self._handler().add_maplayers(pk=999, datasets=[103]))

    def test_cmd_warns_on_empty_dataset_list(self):
        with self.assertLogs(level="WARNING"):
            self._handler().cmd_maplayers_add(pk=42, datasets=[])


class TestRemoveMaplayers(unittest.TestCase):
    def _handler(self):
        return GeonodeMapsHandler(env={})

    @patch.object(GeonodeMapsHandler, "patch")
    @patch.object(GeonodeMapsHandler, "http_get")
    def test_removes_maplayer_and_blob_layer(self, mock_http_get, mock_patch):
        mock_http_get.return_value = _map_detail()
        mock_patch.return_value = {"pk": 42}
        self._handler().remove_maplayers(pk=42, datasets=[101])
        json_content = mock_patch.call_args.kwargs["json_content"]
        self.assertEqual([m["pk"] for m in json_content["maplayers"]], [902])
        layer_ids = [layer["id"] for layer in json_content["data"]["map"]["layers"]]
        self.assertNotIn("msid-101", layer_ids)
        self.assertIn("msid-102", layer_ids)

    @patch.object(GeonodeMapsHandler, "patch")
    @patch.object(GeonodeMapsHandler, "http_get")
    def test_keeps_background_layers(self, mock_http_get, mock_patch):
        mock_http_get.return_value = _map_detail()
        mock_patch.return_value = {"pk": 42}
        self._handler().remove_maplayers(pk=42, datasets=[101, 102])
        json_content = mock_patch.call_args.kwargs["json_content"]
        self.assertEqual(json_content["maplayers"], [])
        layer_ids = [layer["id"] for layer in json_content["data"]["map"]["layers"]]
        self.assertEqual(layer_ids, ["mapnik__0", "none"])

    @patch.object(GeonodeMapsHandler, "patch")
    @patch.object(GeonodeMapsHandler, "http_get")
    def test_renumbers_order(self, mock_http_get, mock_patch):
        detail = _map_detail()
        detail["map"]["maplayers"].append(_maplayer(903, 103, "msid-103", 2))
        detail["map"]["data"]["map"]["layers"].append(_dataset_layer("msid-103", 103))
        mock_http_get.return_value = detail
        mock_patch.return_value = {"pk": 42}
        self._handler().remove_maplayers(pk=42, datasets=[101])
        maplayers = mock_patch.call_args.kwargs["json_content"]["maplayers"]
        self.assertEqual([m["order"] for m in maplayers], [0, 1])

    @patch.object(GeonodeMapsHandler, "patch")
    @patch.object(GeonodeMapsHandler, "http_get")
    def test_removes_mapstore_style_layer_ids(self, mock_http_get, mock_patch):
        """maps edited in MapStore carry `{alternate}__{dataset_pk}` layer ids"""
        detail = _map_detail()
        detail["map"]["data"]["map"]["layers"].append(
            {"id": "geonode:ds101__101", "group": "Default", "name": "geonode:ds101"}
        )
        mock_http_get.return_value = detail
        mock_patch.return_value = {"pk": 42}
        self._handler().remove_maplayers(pk=42, datasets=[101])
        layer_ids = [
            layer["id"]
            for layer in mock_patch.call_args.kwargs["json_content"]["data"]["map"][
                "layers"
            ]
        ]
        self.assertNotIn("geonode:ds101__101", layer_ids)

    @patch.object(GeonodeMapsHandler, "patch")
    @patch.object(GeonodeMapsHandler, "http_get")
    def test_unknown_dataset_is_a_noop(self, mock_http_get, mock_patch):
        mock_http_get.return_value = _map_detail()
        with self.assertLogs(level="WARNING"):
            result = self._handler().remove_maplayers(pk=42, datasets=[999])
        self.assertIsNone(result)
        mock_patch.assert_not_called()

    def test_cmd_warns_on_empty_dataset_list(self):
        with self.assertLogs(level="WARNING"):
            self._handler().cmd_maplayers_remove(pk=42, datasets=[])


class TestCmdMaplayersList(unittest.TestCase):
    def _handler(self):
        return GeonodeMapsHandler(env={})

    @patch.object(GeonodeMapsHandler, "http_get")
    def test_prints_table(self, mock_http_get):
        mock_http_get.return_value = _map_detail()
        with patch("geonoderest.maps.show_list") as mock_show:
            self._handler().cmd_maplayers_list(pk=42, json=False)
        values = mock_show.call_args.kwargs["values"]
        self.assertEqual([row[0] for row in values], ["101", "102"])

    @patch.object(GeonodeMapsHandler, "http_get")
    def test_prints_json_when_requested(self, mock_http_get):
        mock_http_get.return_value = _map_detail()
        with patch("geonoderest.maps.print_json") as mock_print:
            self._handler().cmd_maplayers_list(pk=42, json=True)
        mock_print.assert_called_once()


if __name__ == "__main__":
    unittest.main()
