import unittest
from unittest.mock import patch
from geonoderest.resources import GeonodeResourceHandler, SUPPORTED_METADATA_TYPES


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

    @patch.object(GeonodeResourceHandler, "http_get")
    def test_list(self, mock_http_get):
        mock_http_get.return_value = {"resources": [{"pk": 1}, {"pk": 2}]}
        handler = GeonodeResourceHandler(env={})
        result = handler.list()
        self.assertEqual(len(result), 2)


class TestMetadata(unittest.TestCase):
    def _make_handler(self):
        return GeonodeResourceHandler(env={})

    @patch.object(GeonodeResourceHandler, "http_get_download")
    @patch.object(GeonodeResourceHandler, "http_get")
    def test_metadata_iso_returns_download(self, mock_get, mock_download):
        mock_get.return_value = {
            "resource": {
                "links": [
                    {"name": "ISO", "url": "http://example.com/metadata/iso"},
                    {"name": "Dublin Core", "url": "http://example.com/metadata/dc"},
                ]
            }
        }
        mock_download.return_value = object()
        handler = self._make_handler()
        result = handler.metadata(pk=1, metadata_type="ISO")
        mock_download.assert_called_once_with("http://example.com/metadata/iso")
        self.assertIsNotNone(result)

    @patch.object(GeonodeResourceHandler, "http_get_download")
    @patch.object(GeonodeResourceHandler, "http_get")
    def test_metadata_uses_correct_link_by_name(self, mock_get, mock_download):
        mock_get.return_value = {
            "resource": {
                "links": [
                    {"name": "ISO", "url": "http://example.com/metadata/iso"},
                    {"name": "Dublin Core", "url": "http://example.com/metadata/dc"},
                ]
            }
        }
        mock_download.return_value = object()
        handler = self._make_handler()
        handler.metadata(pk=1, metadata_type="Dublin Core")
        mock_download.assert_called_once_with("http://example.com/metadata/dc")

    @patch.object(GeonodeResourceHandler, "http_get")
    def test_metadata_unsupported_type_raises_valueerror(self, mock_get):
        handler = self._make_handler()
        with self.assertRaises(ValueError) as cm:
            handler.metadata(pk=1, metadata_type="GML")
        self.assertIn("GML", str(cm.exception))
        mock_get.assert_not_called()

    @patch.object(GeonodeResourceHandler, "http_get_download")
    @patch.object(GeonodeResourceHandler, "http_get")
    def test_metadata_type_not_in_links_raises_valueerror(
        self, mock_get, mock_download
    ):
        """Supported type that is simply absent from the resource's links."""
        mock_get.return_value = {
            "resource": {
                "links": [
                    {"name": "ISO", "url": "http://example.com/metadata/iso"},
                ]
            }
        }
        handler = self._make_handler()
        with self.assertRaises(ValueError) as cm:
            handler.metadata(pk=1, metadata_type="Dublin Core")
        self.assertIn("Dublin Core", str(cm.exception))
        mock_download.assert_not_called()

    def test_all_supported_types_are_strings(self):
        """Sanity check: every entry in SUPPORTED_METADATA_TYPES is a non-empty string."""
        for t in SUPPORTED_METADATA_TYPES:
            self.assertIsInstance(t, str)
            self.assertTrue(len(t) > 0)


if __name__ == "__main__":
    unittest.main()
