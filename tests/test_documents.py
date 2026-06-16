import unittest
from unittest.mock import patch
from geonoderest.documents import GeonodeDocumentsHandler
import unittest
from unittest.mock import patch


class TestGeonodeDocumentsHandler(unittest.TestCase):
    @patch.object(GeonodeDocumentsHandler, "http_get")
    def test_get(self, mock_http_get):
        mock_http_get.return_value = {
            "document": [{"pk": 123, "title": "Test Document"}]
        }
        handler = GeonodeDocumentsHandler(env={})
        result = handler.get(123)
        print(result)
        self.assertEqual(result[0]["title"], "Test Document")

    @patch.object(GeonodeDocumentsHandler, "http_patch")
    def test_patch(self, mock_http_patch):
        mock_http_patch.return_value = {"success": True}
        handler = GeonodeDocumentsHandler(env={})
        result = handler.patch(123, json_content={"title": "Updated"})
        self.assertTrue(result["success"])

    @patch.object(GeonodeDocumentsHandler, "http_delete")
    def test_delete_uses_resources_endpoint(self, mock_http_delete):
        """documents API does not allow DELETE — delete must use resources/{pk}/delete."""
        mock_http_delete.return_value = {}
        handler = GeonodeDocumentsHandler(env={})
        handler.delete(pk=7)
        mock_http_delete.assert_called_once_with(endpoint="resources/7/delete")


if __name__ == "__main__":
    unittest.main()
