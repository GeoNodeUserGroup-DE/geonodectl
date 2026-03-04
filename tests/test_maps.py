import unittest
from unittest.mock import patch
from geonoderest.maps import GeonodeMapsHandler


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
    def test_delete_uses_typed_endpoint(self, mock_http_delete):
        """Ensure delete only targets maps, not generic resources endpoint."""
        mock_http_delete.return_value = {}
        handler = GeonodeMapsHandler(env={})
        handler.delete(pk=5)
        mock_http_delete.assert_called_once_with(endpoint="maps/5/")


if __name__ == "__main__":
    unittest.main()
