import unittest
from unittest.mock import patch, call
from geonoderest.datasets import GeonodeDatasetsHandler


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


if __name__ == "__main__":
    unittest.main()
