import json
import os
import tempfile
import unittest
from pathlib import Path

import requests

from unittest.mock import patch, call, MagicMock
from geonoderest.datasets import GeonodeDatasetsHandler
from geonoderest.exceptions import GeoNodeRestException, InvalidPkError
from geonoderest.exitcodes import EXIT_FAILED, EXIT_OK, EXIT_USAGE
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
    def test_delete_uses_resources_endpoint(self, mock_http_delete):
        """datasets API does not allow DELETE — delete must use resources/{pk}/delete."""
        mock_http_delete.return_value = {}
        handler = GeonodeDatasetsHandler(env={})
        handler.delete(pk=5)
        mock_http_delete.assert_called_once_with(endpoint="resources/5/delete")

    @patch.object(GeonodeDatasetsHandler, "http_delete")
    def test_delete_range_uses_resources_endpoint(self, mock_http_delete):
        """datasets API does not allow DELETE — range delete must use resources endpoint."""
        mock_http_delete.return_value = {}
        handler = GeonodeDatasetsHandler(env={})
        for pk in range(1, 4):
            handler.delete(pk=pk)
        calls = [c.kwargs["endpoint"] for c in mock_http_delete.call_args_list]
        self.assertEqual(
            calls, ["resources/1/delete", "resources/2/delete", "resources/3/delete"]
        )


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

    def test_invalid_single_pk_raises(self):
        """a bad pk must raise, not escape as a ValueError or kill the process"""
        with self.assertRaises(InvalidPkError):
            self.handler.__parse_pk_string__("abc")

    def test_invalid_range_bounds_raise(self):
        with self.assertRaises(InvalidPkError):
            self.handler.__parse_pk_string__("a-b")

    def test_malformed_range_raises(self):
        """'1-2-3' used to escape as UnboundLocalError"""
        with self.assertRaises(InvalidPkError):
            self.handler.__parse_pk_string__("1-2-3")

    def test_invalid_pk_list_raises(self):
        with self.assertRaises(InvalidPkError):
            self.handler.__parse_pk_string__("1,a")

    def test_invalid_pk_is_a_value_error(self):
        """subclassing ValueError keeps existing `except ValueError` callers working"""
        self.assertTrue(issubclass(InvalidPkError, ValueError))

    def test_parse_never_exits_the_process(self):
        """library code must not kill its host, see #69"""
        try:
            self.handler.__parse_pk_string__("abc")
        except SystemExit:  # pragma: no cover - the regression we guard against
            self.fail("__parse_pk_string__ must not raise SystemExit")
        except InvalidPkError:
            pass


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


class TestCmdPatchJsonSource(unittest.TestCase):
    """cmd_patch reads its json from --set or --json_path, see #159

    --json_path takes a local path and a http(s) url interchangeably.
    """

    PATCH = {"is_published": True}
    URL = "https://example.org/patch.json"

    def _response(self, payload):
        r = MagicMock()
        r.raise_for_status.return_value = None
        r.json.return_value = payload
        return r

    @patch.object(GeonodeDatasetsHandler, "http_patch")
    def test_patch_from_json_path(self, mock_http_patch):
        mock_http_patch.return_value = {"pk": 42}
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "patch.json")
            with open(path, "w") as f:
                json.dump(self.PATCH, f)
            GeonodeDatasetsHandler(env={}).cmd_patch(pk="42", json_path=path)
        mock_http_patch.assert_called_once_with(
            endpoint="datasets/42/", json_content=self.PATCH
        )

    @patch.object(GeonodeDatasetsHandler, "http_patch")
    @patch("geonoderest.jsonsource.requests.get")
    def test_patch_from_a_url(self, mock_get, mock_http_patch):
        mock_get.return_value = self._response(self.PATCH)
        mock_http_patch.return_value = {"pk": 42}
        GeonodeDatasetsHandler(env={}).cmd_patch(pk="42", json_path=self.URL)
        mock_http_patch.assert_called_once_with(
            endpoint="datasets/42/", json_content=self.PATCH
        )
        self.assertEqual(mock_get.call_args.args[0], self.URL)

    @patch.object(GeonodeDatasetsHandler, "http_patch")
    @patch("geonoderest.jsonsource.requests.get")
    def test_a_url_is_fetched_once_for_a_pk_range(self, mock_get, mock_http_patch):
        """the remote json is read before the loop, not per object"""
        mock_get.return_value = self._response(self.PATCH)
        mock_http_patch.side_effect = lambda endpoint, json_content: {"pk": 1}
        GeonodeDatasetsHandler(env={}).cmd_patch(pk="1-3", json_path=self.URL)
        self.assertEqual(mock_get.call_count, 1)
        self.assertEqual(mock_http_patch.call_count, 3)

    @patch.object(GeonodeDatasetsHandler, "http_patch")
    @patch("geonoderest.jsonsource.requests.get")
    def test_usage_exit_when_the_url_is_unreachable(self, mock_get, mock_http_patch):
        mock_get.side_effect = requests.exceptions.ConnectionError("nope")
        with self.assertLogs(level="ERROR"):
            code = GeonodeDatasetsHandler(env={}).cmd_patch(pk="42", json_path=self.URL)
        self.assertEqual(code, EXIT_USAGE)
        mock_http_patch.assert_not_called()

    @patch.object(GeonodeDatasetsHandler, "http_patch")
    def test_usage_exit_when_the_json_file_is_missing(self, mock_http_patch):
        """used to escape as a raw FileNotFoundError traceback"""
        with self.assertLogs(level="ERROR"):
            code = GeonodeDatasetsHandler(env={}).cmd_patch(
                pk="42", json_path="/nonexistent/nope.json"
            )
        self.assertEqual(code, EXIT_USAGE)
        mock_http_patch.assert_not_called()

    def test_usage_exit_when_no_source_is_given(self):
        with self.assertLogs(level="ERROR"):
            code = GeonodeDatasetsHandler(env={}).cmd_patch(pk="42")
        self.assertEqual(code, EXIT_USAGE)

    @patch.object(GeonodeDatasetsHandler, "http_patch")
    def test_usage_exit_on_an_invalid_pk(self, mock_http_patch):
        with self.assertLogs(level="ERROR"):
            code = GeonodeDatasetsHandler(env={}).cmd_patch(
                pk="abc", fields='{"is_published": true}'
            )
        self.assertEqual(code, EXIT_USAGE)
        mock_http_patch.assert_not_called()


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
    def test_wait_for_upload_raises_on_failure(self, mock_get):
        """library method raises instead of exiting the process, see #69"""
        mock_get.return_value = self._make_er("failed")
        handler = GeonodeDatasetsHandler(env={})
        with self.assertRaises(GeoNodeRestException):
            handler.__wait_for_upload__(exec_id="abc-123", poll_interval=0)

    @patch.object(GeonodeDatasetsHandler, "upload")
    @patch.object(GeonodeExecutionRequestHandler, "get")
    @patch.object(GeonodeDatasetsHandler, "__wait_for_upload__")
    def test_cmd_upload_returns_exit_failed_when_wait_fails(
        self, mock_wait, mock_er_get, mock_upload
    ):
        """the cmd layer turns that exception into an exit code"""
        mock_upload.return_value = {"execution_id": "abc-123"}
        mock_er_get.return_value = {"exec_id": "abc-123"}
        mock_wait.side_effect = GeoNodeRestException("upload failed")
        with self.assertLogs(level="ERROR"):
            code = GeonodeDatasetsHandler(env={}).cmd_upload(
                file_path=Path("x.tif"), wait=True, json=False
            )
        self.assertEqual(code, EXIT_FAILED)

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
