import unittest
from unittest.mock import patch, call, MagicMock
from geonoderest.datasets import GeonodeDatasetsHandler
from geonoderest.executionrequest import GeonodeExecutionRequestHandler


class TestGeonodeDatasetsHandler(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()


class TestGeonodeDatasetHandler(unittest.TestCase):
    @patch.object(GeonodeDatasetsHandler, "http_get")
    def test_get(self, mock_http_get):
        mock_http_get.return_value = {"dataset": [{"pk": 1, "title": "Test Dataset"}]}
        handler = GeonodeDatasetsHandler(env={})
        result = handler.get(123)
        self.assertEqual(result[0]["title"], "Test Dataset")

    @patch.object(GeonodeDatasetsHandler, "http_patch")
    def test_patch(self, mock_http_patch):
        mock_http_patch.return_value = {"success": True}
        handler = GeonodeDatasetsHandler(env={})
        result = handler.patch(123, json_content={"title": "Updated"})
        self.assertTrue(result["success"])


if __name__ == "__main__":
    unittest.main()


class TestWaitForUpload(unittest.TestCase):
    """Tests for __wait_for_upload__ and cmd_upload --wait.
    Feature test for: https://github.com/GeoNodeUserGroup-DE/geonodectl/issues/80
    """

    def _make_er(self, status, pks=None):
        resources = [{"id": pk} for pk in (pks or [])]
        return {"status": status, "output_params": {"resources": resources}}

    @patch.object(GeonodeExecutionRequestHandler, "get")
    def test_wait_for_upload_returns_pks_on_success(self, mock_get):
        """__wait_for_upload__ returns PKs when execution finishes successfully."""
        mock_get.return_value = self._make_er("finished", pks=[42, 43])
        handler = GeonodeDatasetsHandler(env={})
        pks = handler.__wait_for_upload__(exec_id="abc-123", poll_interval=0)
        self.assertEqual(pks, [42, 43])

    @patch.object(GeonodeExecutionRequestHandler, "get")
    def test_wait_for_upload_polls_until_finished(self, mock_get):
        """__wait_for_upload__ polls until status is 'finished'."""
        mock_get.side_effect = [
            self._make_er("running"),
            self._make_er("running"),
            self._make_er("finished", pks=[7]),
        ]
        handler = GeonodeDatasetsHandler(env={})
        pks = handler.__wait_for_upload__(exec_id="abc-123", poll_interval=0)
        self.assertEqual(mock_get.call_count, 3)
        self.assertEqual(pks, [7])

    @patch.object(GeonodeExecutionRequestHandler, "get")
    def test_wait_for_upload_exits_on_failure(self, mock_get):
        """__wait_for_upload__ calls sys.exit when upload fails."""
        mock_get.return_value = self._make_er("failed")
        handler = GeonodeDatasetsHandler(env={})
        with self.assertRaises(SystemExit):
            handler.__wait_for_upload__(exec_id="abc-123", poll_interval=0)

    @patch.object(GeonodeDatasetsHandler, "__wait_for_upload__")
    @patch.object(GeonodeDatasetsHandler, "get")
    @patch.object(GeonodeDatasetsHandler, "upload")
    @patch.object(GeonodeExecutionRequestHandler, "get")
    def test_cmd_upload_with_wait_describes_resulting_datasets(
        self, mock_er_get, mock_upload, mock_ds_get, mock_wait
    ):
        """cmd_upload with wait=True waits and then describes each resulting dataset."""
        mock_upload.return_value = {"execution_id": "exec-001"}
        mock_er_get.return_value = {
            "status": "running",
            "exec_id": "exec-001",
            "created": "",
            "name": "",
            "link": "",
        }
        mock_wait.return_value = [10, 11]
        mock_ds_get.side_effect = lambda pk, **kw: {"pk": pk, "title": f"DS {pk}"}

        handler = GeonodeDatasetsHandler(env={})
        from pathlib import Path

        handler.cmd_upload(
            file_path=Path("/fake/file.gpkg"),
            wait=True,
            json=True,
        )
        mock_wait.assert_called_once_with(exec_id="exec-001")
        self.assertEqual(mock_ds_get.call_count, 2)

    @patch.object(GeonodeDatasetsHandler, "upload")
    @patch.object(GeonodeExecutionRequestHandler, "get")
    def test_cmd_upload_without_wait_shows_execution_request(
        self, mock_er_get, mock_upload
    ):
        """cmd_upload without --wait shows the execution request info (existing behaviour)."""
        mock_upload.return_value = {"execution_id": "exec-002"}
        mock_er_get.return_value = {
            "status": "started",
            "exec_id": "exec-002",
            "created": "2026-01-01",
            "name": "import",
            "link": "http://x",
        }
        handler = GeonodeDatasetsHandler(env={})
        from pathlib import Path

        # Should not raise; wait=False is default
        handler.cmd_upload(file_path=Path("/fake/file.gpkg"), wait=False, json=True)
        mock_er_get.assert_called_once()


if __name__ == "__main__":
    unittest.main()
