import unittest
from unittest.mock import patch, MagicMock
from geonoderest.datasets import GeonodeDatasetsHandler
from geonoderest.cmdprint import print_list_on_cmd


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
