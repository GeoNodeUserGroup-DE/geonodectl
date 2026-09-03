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
    def test_requests_blob_with_include_param(self, mock_http_get):
        mock_http_get.return_value = {"map": {"pk": 42, "blob": BLOB}}
        with patch("geonoderest.maps.print_json"):
            self._handler().cmd_get_blob(pk=42)
        mock_http_get.assert_called_once_with("maps/42/", params={"include[]": "blob"})

    @patch.object(GeonodeMapsHandler, "http_get")
    def test_prints_blob(self, mock_http_get):
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
        mock_http_get.return_value = {"map": {"pk": 42, "blob": {}}}
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
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(BLOB, f)
            path = f.name
        with patch("geonoderest.maps.print_json"):
            self._handler().cmd_set_blob(pk=42, json_path=path)
        args, kwargs = mock_patch.call_args
        self.assertEqual(kwargs["json_content"]["blob"], BLOB)

    @patch.object(GeonodeMapsHandler, "http_patch")
    def test_prints_result_on_success(self, mock_patch):
        mock_patch.return_value = {"map": {"pk": 42, "title": "T"}}
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(BLOB, f)
            path = f.name
        with patch("geonoderest.maps.print_json") as mock_print:
            self._handler().cmd_set_blob(pk=42, json_path=path)
        mock_print.assert_called_once()

    @patch.object(GeonodeMapsHandler, "http_patch", return_value=None)
    def test_logs_error_when_patch_fails(self, _):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(BLOB, f)
            path = f.name
        with self.assertLogs(level="ERROR"):
            self._handler().cmd_set_blob(pk=42, json_path=path)

    def test_raises_when_no_json_path(self):
        with self.assertRaises(ValueError):
            self._handler().cmd_set_blob(pk=42, json_path=None)


if __name__ == "__main__":
    unittest.main()
