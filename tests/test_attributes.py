import unittest
from unittest.mock import patch
from geonoderest.attributes import GeonodeAttributeHandler


class TestGeonodeAttributeHandler(unittest.TestCase):
    @patch.object(GeonodeAttributeHandler, "http_get")
    def test_get(self, mock_http_get):
        mock_http_get.return_value = {"attributes": [{"pk": 1, "attribute": "name"}]}
        handler = GeonodeAttributeHandler(env={})
        result = handler.get(123)
        self.assertEqual(result["attributes"][0]["attribute"], "name")

    @patch.object(GeonodeAttributeHandler, "http_patch")
    def test_patch(self, mock_http_patch):
        mock_http_patch.return_value = {"success": True}
        handler = GeonodeAttributeHandler(env={})
        result = handler.patch(123, json_content={"attribute_set": []})
        self.assertTrue(result["success"])


if __name__ == "__main__":
    unittest.main()
