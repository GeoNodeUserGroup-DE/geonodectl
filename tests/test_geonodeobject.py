import unittest
from unittest.mock import patch, MagicMock

from geonoderest.datasets import GeonodeDatasetsHandler
from geonoderest.geonodeobject import GeonodeObjectHandler
from geonoderest.maps import GeonodeMapsHandler


class TestParsePkString(unittest.TestCase):
    """Tests for __parse_delete_pk_string__ covering all pk input formats."""

    def setUp(self):
        self.handler = GeonodeObjectHandler(env={})
        self.handler.ENDPOINT_NAME = "resources"
        self.handler.JSON_OBJECT_NAME = "resources"

    # --- single pk ---

    def test_single_pk(self):
        self.assertEqual(self.handler.__parse_delete_pk_string__("5"), [5])

    def test_single_pk_one(self):
        self.assertEqual(self.handler.__parse_delete_pk_string__("1"), [1])

    def test_single_pk_not_integer_raises(self):
        with self.assertRaises(SystemExit):
            self.handler.__parse_delete_pk_string__("abc")

    # --- range pk ---

    def test_range_pk(self):
        self.assertEqual(self.handler.__parse_delete_pk_string__("3-6"), [3, 4, 5, 6])

    def test_range_pk_single_element(self):
        """Range of one element: start == end."""
        self.assertEqual(self.handler.__parse_delete_pk_string__("5-5"), [5])

    def test_range_reversed_raises(self):
        """Range where start > end must raise, not silently produce empty list."""
        with self.assertRaises(SystemExit) as cm:
            self.handler.__parse_delete_pk_string__("10-3")
        self.assertIn("10", str(cm.exception))

    def test_range_non_integer_start_raises(self):
        with self.assertRaises(SystemExit):
            self.handler.__parse_delete_pk_string__("a-5")

    def test_range_non_integer_end_raises(self):
        with self.assertRaises(SystemExit):
            self.handler.__parse_delete_pk_string__("1-z")

    def test_range_too_many_parts_raises(self):
        """'1-2-3' cannot be split into exactly two parts."""
        with self.assertRaises(SystemExit):
            self.handler.__parse_delete_pk_string__("1-2-3")

    # --- list pk ---

    def test_list_pk(self):
        self.assertEqual(self.handler.__parse_delete_pk_string__("1,2,3"), [1, 2, 3])

    def test_list_pk_single_element(self):
        """A comma-delimited list with a trailing comma is invalid input."""
        with self.assertRaises(SystemExit):
            self.handler.__parse_delete_pk_string__("7,")

    def test_list_pk_non_integer_raises(self):
        with self.assertRaises(SystemExit):
            self.handler.__parse_delete_pk_string__("1,two,3")

    def test_list_pk_preserves_order(self):
        self.assertEqual(
            self.handler.__parse_delete_pk_string__("10,5,20"), [10, 5, 20]
        )


class TestCmdDeleteDispatch(unittest.TestCase):
    """Tests for cmd_delete: pk parsing → delete() calls."""

    @patch.object(GeonodeDatasetsHandler, "http_delete")
    def test_cmd_delete_single(self, mock_delete):
        mock_delete.return_value = {}
        handler = GeonodeDatasetsHandler(env={})
        handler.cmd_delete(pk="42")
        mock_delete.assert_called_once_with(endpoint="datasets/42/")

    @patch.object(GeonodeDatasetsHandler, "http_delete")
    def test_cmd_delete_range(self, mock_delete):
        mock_delete.return_value = {}
        handler = GeonodeDatasetsHandler(env={})
        handler.cmd_delete(pk="1-3")
        endpoints = [c.kwargs["endpoint"] for c in mock_delete.call_args_list]
        self.assertEqual(endpoints, ["datasets/1/", "datasets/2/", "datasets/3/"])

    @patch.object(GeonodeDatasetsHandler, "http_delete")
    def test_cmd_delete_list(self, mock_delete):
        mock_delete.return_value = {}
        handler = GeonodeDatasetsHandler(env={})
        handler.cmd_delete(pk="5,10,15")
        endpoints = [c.kwargs["endpoint"] for c in mock_delete.call_args_list]
        self.assertEqual(endpoints, ["datasets/5/", "datasets/10/", "datasets/15/"])

    @patch.object(GeonodeDatasetsHandler, "http_delete")
    def test_cmd_delete_invalid_pk_raises(self, mock_delete):
        handler = GeonodeDatasetsHandler(env={})
        with self.assertRaises(SystemExit):
            handler.cmd_delete(pk="not-a-number")

    @patch.object(GeonodeDatasetsHandler, "http_delete")
    def test_cmd_delete_reversed_range_raises(self, mock_delete):
        handler = GeonodeDatasetsHandler(env={})
        with self.assertRaises(SystemExit):
            handler.cmd_delete(pk="10-1")


class TestCmdPatch(unittest.TestCase):
    """Tests for cmd_patch: JSON fields and json_path parsing."""

    @patch.object(GeonodeDatasetsHandler, "http_patch")
    def test_cmd_patch_from_fields(self, mock_patch):
        mock_patch.return_value = {"pk": 1, "title": "Updated"}
        handler = GeonodeDatasetsHandler(env={})
        handler.cmd_patch(pk=1, fields='{"title": "Updated"}', json_path=None)
        mock_patch.assert_called_once()
        _, kwargs = mock_patch.call_args
        self.assertEqual(kwargs["json_content"]["title"], "Updated")

    @patch.object(GeonodeDatasetsHandler, "http_patch")
    def test_cmd_patch_invalid_json_does_not_raise_unbound(self, mock_patch):
        """Malformed JSON must not cause UnboundLocalError on json_content."""
        handler = GeonodeDatasetsHandler(env={})
        # json_decode_error_handler raises SystemExit internally
        with self.assertRaises(SystemExit):
            handler.cmd_patch(pk=1, fields="{bad json}", json_path=None)
        mock_patch.assert_not_called()

    @patch.object(GeonodeDatasetsHandler, "http_patch")
    def test_cmd_patch_no_fields_no_path_raises_valueerror(self, mock_patch):
        handler = GeonodeDatasetsHandler(env={})
        with self.assertRaises(ValueError):
            handler.cmd_patch(pk=1, fields=None, json_path=None)


class TestList(unittest.TestCase):
    """Tests for list() on various handler types."""

    @patch.object(GeonodeDatasetsHandler, "http_get")
    def test_list_datasets(self, mock_get):
        mock_get.return_value = {"datasets": [{"pk": 1}, {"pk": 2}]}
        handler = GeonodeDatasetsHandler(env={})
        result = handler.list()
        self.assertEqual(len(result), 2)
        mock_get.assert_called_once_with(endpoint="datasets/", params={})

    @patch.object(GeonodeMapsHandler, "http_get")
    def test_list_maps(self, mock_get):
        mock_get.return_value = {"maps": [{"pk": 10}]}
        handler = GeonodeMapsHandler(env={})
        result = handler.list()
        self.assertEqual(result[0]["pk"], 10)
        mock_get.assert_called_once_with(endpoint="maps/", params={})

    @patch.object(GeonodeDatasetsHandler, "http_get")
    def test_list_returns_none_on_http_failure(self, mock_get):
        mock_get.return_value = None
        handler = GeonodeDatasetsHandler(env={})
        result = handler.list()
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
