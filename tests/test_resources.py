import unittest
from unittest.mock import patch
from geonoderest.resources import GeonodeResourceHandler


class TestGeonodeResourcesHandler(unittest.TestCase):
    @patch.object(GeonodeResourceHandler, "http_get")
    def test_get(self, mock_http_get):
        mock_http_get.return_value = {"resource": {"pk": 123, "title": "Test Resource"}}
        handler = GeonodeResourceHandler(env={})
        result = handler.get(123)
        self.assertEqual(result["title"], "Test Resource")

    @patch.object(GeonodeResourceHandler, "http_patch")
    def test_patch(self, mock_http_patch):
        mock_http_patch.return_value = {"success": True}
        handler = GeonodeResourceHandler(env={})
        result = handler.patch(123, json_content={"title": "Updated"})
        self.assertTrue(result["success"])


if __name__ == "__main__":
    unittest.main()
