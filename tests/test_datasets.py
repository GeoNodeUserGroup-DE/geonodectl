import unittest

from unittest.mock import patch, call, MagicMock
from geonoderest.datasets import GeonodeDatasetsHandler
from geonoderest.cmdprint import print_list_on_cmd
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


class TestCmdListNoneHandling(unittest.TestCase):
    """Tests for graceful handling when API returns None (e.g. invalid filter or error response).
    Regression test for: https://github.com/GeoNodeUserGroup-DE/geonodectl/issues/121
    """

    @patch.object(GeonodeDatasetsHandler, "list")
    def test_cmd_list_does_not_crash_when_api_returns_none(self, mock_list):
        """cmd_list must not raise TypeError when list() returns None."""
        mock_list.return_value = None
        handler = GeonodeDatasetsHandler(env={})
        try:
            handler.cmd_list(json=False, filter={"is_featured": "true"})
        except TypeError as e:
            self.fail(f"cmd_list raised TypeError unexpectedly: {e}")

    @patch.object(GeonodeDatasetsHandler, "list")
    def test_cmd_list_json_does_not_crash_when_api_returns_none(self, mock_list):
        """cmd_list with --json flag must not crash when list() returns None."""
        mock_list.return_value = None
        handler = GeonodeDatasetsHandler(env={})
        try:
            handler.cmd_list(json=True, filter={"is_featured": "true"})
        except TypeError as e:
            self.fail(f"cmd_list raised TypeError unexpectedly: {e}")

    def test_print_list_on_cmd_does_not_crash_on_none(self):
        """print_list_on_cmd must not raise TypeError when obj is None."""
        try:
            print_list_on_cmd(None, [])
        except TypeError as e:
            self.fail(f"print_list_on_cmd raised TypeError unexpectedly: {e}")

    @patch.object(GeonodeDatasetsHandler, "list")
    def test_cmd_list_works_normally_with_valid_results(self, mock_list):
        """cmd_list must still work correctly when list() returns valid data."""
        mock_list.return_value = [
            {
                "pk": 1,
                "title": "Test Dataset",
                "owner": {"username": "admin"},
                "date": "2026-01-01",
                "is_approved": True,
                "is_published": True,
                "state": "PROCESSED",
                "detail_url": "/datasets/1",
            }
        ]
        handler = GeonodeDatasetsHandler(env={})
        try:
            handler.cmd_list(json=False, filter={})
        except Exception as e:
            self.fail(f"cmd_list raised unexpectedly: {e}")


if __name__ == "__main__":
    unittest.main()


class TestPkRangeParsing(unittest.TestCase):
    """Tests for __parse_pk_string__ range/list/single pk parsing.
    Regression/feature test for: https://github.com/GeoNodeUserGroup-DE/geonodectl/issues/122
    """

    def setUp(self):
        self.handler = GeonodeDatasetsHandler(env={})

    def test_parse_single_pk(self):
        self.assertEqual(self.handler.__parse_pk_string__("42"), [42])

    def test_parse_pk_range(self):
        self.assertEqual(self.handler.__parse_pk_string__("5-8"), [5, 6, 7, 8])

    def test_parse_pk_list(self):
        self.assertEqual(self.handler.__parse_pk_string__("1,2,3"), [1, 2, 3])


class TestCmdPatchRange(unittest.TestCase):
    """Tests for cmd_patch range/list/single pk execution.
    Feature test for: https://github.com/GeoNodeUserGroup-DE/geonodectl/issues/122
    """

    def _make_patch_return(self, pk):
        return {"pk": pk, "title": f"Updated {pk}"}

    @patch.object(GeonodeDatasetsHandler, "http_patch")
    def test_cmd_patch_single_pk(self, mock_http_patch):
        """cmd_patch with a single pk patches exactly one resource."""
        mock_http_patch.return_value = self._make_patch_return(42)
        handler = GeonodeDatasetsHandler(env={})
        handler.cmd_patch(pk="42", fields='{"is_published": true}')
        mock_http_patch.assert_called_once_with(
            endpoint="datasets/42/", json_content={"is_published": True}
        )

    @patch.object(GeonodeDatasetsHandler, "http_patch")
    def test_cmd_patch_range(self, mock_http_patch):
        """cmd_patch with a range patches each resource in the range."""
        mock_http_patch.side_effect = lambda endpoint, json_content: {
            "pk": int(endpoint.split("/")[-2])
        }
        handler = GeonodeDatasetsHandler(env={})
        handler.cmd_patch(pk="1-3", fields='{"is_published": true}')
        endpoints = [c.kwargs["endpoint"] for c in mock_http_patch.call_args_list]
        self.assertEqual(endpoints, ["datasets/1/", "datasets/2/", "datasets/3/"])

    @patch.object(GeonodeDatasetsHandler, "http_patch")
    def test_cmd_patch_list(self, mock_http_patch):
        """cmd_patch with a comma-separated list patches each resource in the list."""
        mock_http_patch.side_effect = lambda endpoint, json_content: {
            "pk": int(endpoint.split("/")[-2])
        }
        handler = GeonodeDatasetsHandler(env={})
        handler.cmd_patch(pk="10,20,30", fields='{"is_published": true}')
        endpoints = [c.kwargs["endpoint"] for c in mock_http_patch.call_args_list]
        self.assertEqual(endpoints, ["datasets/10/", "datasets/20/", "datasets/30/"])


class TestCmdDescribeRange(unittest.TestCase):
    """Tests for cmd_describe range/list/single pk execution.
    Feature test for: https://github.com/GeoNodeUserGroup-DE/geonodectl/issues/122
    """

    def _make_get_return(self, pk):
        return {
            GeonodeDatasetsHandler.SINGULAR_RESOURCE_NAME: {
                "pk": pk,
                "title": f"Dataset {pk}",
            }
        }

    @patch.object(GeonodeDatasetsHandler, "http_get")
    def test_cmd_describe_single_pk(self, mock_http_get):
        """cmd_describe with a single pk fetches exactly one resource."""
        mock_http_get.return_value = self._make_get_return(42)
        handler = GeonodeDatasetsHandler(env={})
        handler.cmd_describe(pk="42")
        mock_http_get.assert_called_once_with(endpoint="datasets/42")

    @patch.object(GeonodeDatasetsHandler, "http_get")
    def test_cmd_describe_range(self, mock_http_get):
        """cmd_describe with a range fetches each resource in the range."""
        mock_http_get.side_effect = lambda endpoint: self._make_get_return(
            int(endpoint.split("/")[-1])
        )
        handler = GeonodeDatasetsHandler(env={})
        handler.cmd_describe(pk="1-3")
        endpoints = [c.kwargs["endpoint"] for c in mock_http_get.call_args_list]
        self.assertEqual(endpoints, ["datasets/1", "datasets/2", "datasets/3"])

    @patch.object(GeonodeDatasetsHandler, "http_get")
    def test_cmd_describe_list(self, mock_http_get):
        """cmd_describe with a comma-separated list fetches each resource in the list."""
        mock_http_get.side_effect = lambda endpoint: self._make_get_return(
            int(endpoint.split("/")[-1])
        )
        handler = GeonodeDatasetsHandler(env={})
        handler.cmd_describe(pk="10,20,30")
        endpoints = [c.kwargs["endpoint"] for c in mock_http_get.call_args_list]
        self.assertEqual(endpoints, ["datasets/10", "datasets/20", "datasets/30"])


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
