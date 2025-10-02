import unittest
from unittest.mock import patch
from geonoderest.geoapps import GeonodeGeoappsHandler


class TestGeonodeGeoAppsHandler(unittest.TestCase):
    @patch.object(GeonodeGeoappsHandler, "http_get")
    def test_get(self, mock_http_get):
        mock_http_get.return_value = {"geoapp": {"pk": 1, "title": "Test GeoApp"}}
        handler = GeonodeGeoappsHandler(env={})
        result = handler.get(123)
        self.assertEqual(result["title"], "Test GeoApp")

    @patch.object(GeonodeGeoappsHandler, "http_patch")
    def test_patch(self, mock_http_patch):
        mock_http_patch.return_value = {"success": True}
        handler = GeonodeGeoappsHandler(env={})
        result = handler.patch(123, json_content={"title": "Updated"})
        self.assertTrue(result["success"])


if __name__ == "__main__":
    unittest.main()
