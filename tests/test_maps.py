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


if __name__ == "__main__":
    unittest.main()
