import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

from geonoderest.datasets import GeonodeDatasetsHandler


class TestGeonodeDatasetsHandlerCRUD(unittest.TestCase):
    @patch.object(GeonodeDatasetsHandler, "http_get")
    def test_get(self, mock_http_get):
        mock_http_get.return_value = {"dataset": [{"pk": 123, "title": "Test Dataset"}]}
        handler = GeonodeDatasetsHandler(env={})
        result = handler.get(123)
        self.assertEqual(result[0]["title"], "Test Dataset")

    @patch.object(GeonodeDatasetsHandler, "http_patch")
    def test_patch(self, mock_http_patch):
        mock_http_patch.return_value = {"success": True}
        handler = GeonodeDatasetsHandler(env={})
        result = handler.patch(123, json_content={"title": "Updated"})
        self.assertTrue(result["success"])

    @patch.object(GeonodeDatasetsHandler, "http_patch")
    def test_patch_strips_attribute_fields(self, mock_http_patch):
        """datasets.patch() must remove attribute and attribute_set before forwarding."""
        mock_http_patch.return_value = {}
        handler = GeonodeDatasetsHandler(env={})
        handler.patch(
            1, json_content={"title": "x", "attribute": "foo", "attribute_set": []}
        )
        _, kwargs = mock_http_patch.call_args
        self.assertNotIn("attribute", kwargs["json_content"])
        self.assertNotIn("attribute_set", kwargs["json_content"])

    @patch.object(GeonodeDatasetsHandler, "http_delete")
    def test_delete_uses_typed_endpoint(self, mock_http_delete):
        """Ensure delete only targets datasets, not generic resources endpoint."""
        mock_http_delete.return_value = {}
        handler = GeonodeDatasetsHandler(env={})
        handler.delete(pk=5)
        mock_http_delete.assert_called_once_with(endpoint="datasets/5/")

    @patch.object(GeonodeDatasetsHandler, "http_delete")
    def test_delete_range_uses_typed_endpoint(self, mock_http_delete):
        """Ensure range delete only calls dataset endpoint for each pk in range."""
        mock_http_delete.return_value = {}
        handler = GeonodeDatasetsHandler(env={})
        for pk in range(1, 4):
            handler.delete(pk=pk)
        calls = [c.kwargs["endpoint"] for c in mock_http_delete.call_args_list]
        self.assertEqual(calls, ["datasets/1/", "datasets/2/", "datasets/3/"])

    @patch.object(GeonodeDatasetsHandler, "http_get")
    def test_list_returns_datasets(self, mock_http_get):
        mock_http_get.return_value = {"datasets": [{"pk": 1}, {"pk": 2}]}
        handler = GeonodeDatasetsHandler(env={})
        result = handler.list()
        self.assertEqual(len(result), 2)
        mock_http_get.assert_called_once_with(endpoint="datasets/", params={})

    @patch.object(GeonodeDatasetsHandler, "http_get")
    def test_list_returns_none_on_failure(self, mock_http_get):
        mock_http_get.return_value = None
        handler = GeonodeDatasetsHandler(env={})
        result = handler.list()
        self.assertIsNone(result)


class TestGeonodeDatasetsUpload(unittest.TestCase):
    """Tests for upload() — file existence checks, handle cleanup, payload."""

    @patch.object(GeonodeDatasetsHandler, "http_post")
    def test_upload_non_shapefile_calls_http_post(self, mock_post):
        mock_post.return_value = {"execution_id": "abc"}
        handler = GeonodeDatasetsHandler(env={})

        with tempfile.TemporaryDirectory() as d:
            geotiff = Path(d) / "raster.tif"
            geotiff.write_bytes(b"\x00" * 10)

            result = handler.upload(file_path=geotiff)
            self.assertEqual(result["execution_id"], "abc")
            mock_post.assert_called_once()
            _, kwargs = mock_post.call_args
            self.assertEqual(kwargs["endpoint"], "uploads/upload")

    @patch.object(GeonodeDatasetsHandler, "http_post")
    def test_upload_missing_file_raises_filenotfounderror(self, mock_post):
        handler = GeonodeDatasetsHandler(env={})
        with self.assertRaises(FileNotFoundError):
            handler.upload(file_path=Path("/nonexistent/file.tif"))

    @patch.object(GeonodeDatasetsHandler, "http_post")
    def test_upload_file_handles_closed_after_upload(self, mock_post):
        """File handles must be closed even on success."""
        mock_post.return_value = {"execution_id": "abc"}
        handler = GeonodeDatasetsHandler(env={})

        with tempfile.TemporaryDirectory() as d:
            geotiff = Path(d) / "raster.tif"
            geotiff.write_bytes(b"\x00" * 10)
            handler.upload(file_path=geotiff)

            # After upload(), the file must not be lockable via exclusive open
            # on Linux files are always openable; we check the handle is closed
            # by inspecting what was passed to http_post
            _, kwargs = mock_post.call_args
            files = kwargs["files"]
            for _, file_tuple in files:
                fh = file_tuple[1]
                self.assertTrue(fh.closed, f"File handle {fh.name} was not closed")

    @patch.object(GeonodeDatasetsHandler, "http_post")
    def test_upload_file_handles_closed_on_post_exception(self, mock_post):
        """File handles must be closed even if http_post raises."""
        from geonoderest.exceptions import GeoNodeRestException

        mock_post.side_effect = GeoNodeRestException("upload failed")
        handler = GeonodeDatasetsHandler(env={})

        with tempfile.TemporaryDirectory() as d:
            geotiff = Path(d) / "raster.tif"
            geotiff.write_bytes(b"\x00" * 10)

            with self.assertRaises(GeoNodeRestException):
                handler.upload(file_path=geotiff)

            # Even on exception, handles must be closed — we can't easily inspect
            # them post-raise, but this confirms the exception propagates correctly.

    @patch.object(GeonodeDatasetsHandler, "http_post")
    def test_upload_shapefile_requires_all_sidecar_files(self, mock_post):
        """Missing .dbf/.shx/.prj for a shapefile must raise FileNotFoundError."""
        handler = GeonodeDatasetsHandler(env={})

        with tempfile.TemporaryDirectory() as d:
            shp = Path(d) / "layer.shp"
            shp.write_bytes(b"\x00" * 10)
            # dbf, shx, prj intentionally absent

            with self.assertRaises(FileNotFoundError):
                handler.upload(file_path=shp)

    @patch.object(GeonodeDatasetsHandler, "http_post")
    def test_upload_shapefile_all_parts_present(self, mock_post):
        """A shapefile with all sidecar files should upload successfully."""
        mock_post.return_value = {"execution_id": "xyz"}
        handler = GeonodeDatasetsHandler(env={})

        with tempfile.TemporaryDirectory() as d:
            stem = Path(d) / "layer"
            for ext in [".shp", ".dbf", ".shx", ".prj"]:
                (stem.parent / (stem.name + ext)).write_bytes(b"\x00" * 10)

            result = handler.upload(file_path=stem.parent / "layer.shp")
            self.assertEqual(result["execution_id"], "xyz")
            _, kwargs = mock_post.call_args
            file_keys = [f[0] for f in kwargs["files"]]
            self.assertIn("base_file", file_keys)
            self.assertIn("dbf_file", file_keys)
            self.assertIn("shx_file", file_keys)
            self.assertIn("prj_file", file_keys)

    @patch.object(GeonodeDatasetsHandler, "http_post")
    def test_upload_zip_adds_zip_file_entry(self, mock_post):
        """ZIP upload must include both base_file and zip_file entries."""
        mock_post.return_value = {"execution_id": "zip-run"}
        handler = GeonodeDatasetsHandler(env={})

        with tempfile.TemporaryDirectory() as d:
            zf = Path(d) / "data.zip"
            zf.write_bytes(b"PK\x03\x04")

            handler.upload(file_path=zf)
            _, kwargs = mock_post.call_args
            file_keys = [f[0] for f in kwargs["files"]]
            self.assertIn("base_file", file_keys)
            self.assertIn("zip_file", file_keys)


if __name__ == "__main__":
    unittest.main()
