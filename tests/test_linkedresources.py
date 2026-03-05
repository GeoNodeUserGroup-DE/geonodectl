import unittest
from unittest.mock import patch, MagicMock

from geonoderest.linkedresources import GeonodeLinkedResourcesHandler


class TestLinkedResourcesAdd(unittest.TestCase):
    @patch.object(GeonodeLinkedResourcesHandler, "http_post")
    @patch.object(GeonodeLinkedResourcesHandler, "http_get")
    def test_add_posts_correct_endpoint_and_payload(self, mock_get, mock_post):
        mock_get.return_value = {"linked_to": [], "linked_by": []}
        mock_post.return_value = {"success": True}

        handler = GeonodeLinkedResourcesHandler(env={})
        result = handler.add(pk=1, linked_to=[10, 20])

        mock_post.assert_called_once_with(
            endpoint="resources/1/linked_resources",
            json={"target": [10, 20]},
        )
        self.assertEqual(result["success"], True)

    @patch.object(GeonodeLinkedResourcesHandler, "http_post")
    @patch.object(GeonodeLinkedResourcesHandler, "http_get")
    def test_add_empty_linked_to_sends_empty_target(self, mock_get, mock_post):
        mock_get.return_value = {"linked_to": [], "linked_by": []}
        mock_post.return_value = {}

        handler = GeonodeLinkedResourcesHandler(env={})
        handler.add(pk=5, linked_to=None)

        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs["json"]["target"], [])


class TestLinkedResourcesDelete(unittest.TestCase):
    @patch.object(GeonodeLinkedResourcesHandler, "http_delete")
    def test_delete_posts_correct_endpoint_and_payload(self, mock_delete):
        mock_delete.return_value = {}

        handler = GeonodeLinkedResourcesHandler(env={})
        handler.delete(pk=3, linked_to=[7, 8])

        mock_delete.assert_called_once_with(
            endpoint="resources/3/linked_resources",
            json={"target": [7, 8]},
        )

    @patch.object(GeonodeLinkedResourcesHandler, "http_delete")
    def test_delete_none_linked_to_sends_empty_target(self, mock_delete):
        mock_delete.return_value = {}
        handler = GeonodeLinkedResourcesHandler(env={})
        handler.delete(pk=3, linked_to=None)

        _, kwargs = mock_delete.call_args
        self.assertEqual(kwargs["json"]["target"], [])


class TestLinkedResourcesGet(unittest.TestCase):
    @patch.object(GeonodeLinkedResourcesHandler, "http_get")
    def test_get_calls_correct_endpoint(self, mock_get):
        mock_get.return_value = {"linked_to": [], "linked_by": []}
        handler = GeonodeLinkedResourcesHandler(env={})
        result = handler.get(pk=42)

        mock_get.assert_called_once_with(endpoint="resources/42/linked_resources")
        self.assertIn("linked_to", result)


class TestLinkedResourcesCmdAdd(unittest.TestCase):
    @patch.object(GeonodeLinkedResourcesHandler, "add")
    def test_cmd_add_no_linked_to_exits(self, mock_add):
        handler = GeonodeLinkedResourcesHandler(env={})
        with self.assertRaises(SystemExit):
            handler.cmd_add(pk=1, linked_to=None)
        mock_add.assert_not_called()

    @patch.object(GeonodeLinkedResourcesHandler, "add")
    def test_cmd_add_empty_list_exits(self, mock_add):
        handler = GeonodeLinkedResourcesHandler(env={})
        with self.assertRaises(SystemExit):
            handler.cmd_add(pk=1, linked_to=[])
        mock_add.assert_not_called()

    @patch.object(GeonodeLinkedResourcesHandler, "add")
    def test_cmd_add_calls_add_with_correct_args(self, mock_add):
        mock_add.return_value = {"linked_to": [10]}
        handler = GeonodeLinkedResourcesHandler(env={})
        handler.cmd_add(pk=1, linked_to=[10])
        mock_add.assert_called_once_with(pk=1, linked_to=[10])


class TestLinkedResourcesCmdDelete(unittest.TestCase):
    @patch.object(GeonodeLinkedResourcesHandler, "delete")
    def test_cmd_delete_no_linked_to_exits(self, mock_delete):
        handler = GeonodeLinkedResourcesHandler(env={})
        with self.assertRaises(SystemExit):
            handler.cmd_delete(pk=1, linked_to=None)
        mock_delete.assert_not_called()

    @patch.object(GeonodeLinkedResourcesHandler, "delete")
    def test_cmd_delete_calls_delete_with_correct_args(self, mock_delete):
        mock_delete.return_value = {}
        handler = GeonodeLinkedResourcesHandler(env={})
        handler.cmd_delete(pk=2, linked_to=[5, 6])
        mock_delete.assert_called_once_with(pk=2, linked_to=[5, 6])


if __name__ == "__main__":
    unittest.main()
