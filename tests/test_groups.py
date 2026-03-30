import unittest
from unittest.mock import patch

from geonoderest.groups import GeonodeGroupsHandler


class TestGeonodeGroupsHandler(unittest.TestCase):

    @patch.object(GeonodeGroupsHandler, "http_get")
    def test_list(self, mock_http_get):
        """Ensure list calls the groups endpoint and returns groups list."""
        mock_http_get.return_value = {
            "groups": [
                {"pk": 1, "title": "Group A", "name": "group-a", "description": ""},
                {"pk": 2, "title": "Group B", "name": "group-b", "description": ""},
            ]
        }
        handler = GeonodeGroupsHandler(env={})
        result = handler.list()
        mock_http_get.assert_called_once_with(endpoint="groups/", params={})
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["title"], "Group A")

    @patch.object(GeonodeGroupsHandler, "http_get")
    def test_get(self, mock_http_get):
        """Ensure get returns the 'group' dict from the API response."""
        mock_http_get.return_value = {
            "group": {"pk": 1, "title": "Group A", "name": "group-a", "description": ""}
        }
        handler = GeonodeGroupsHandler(env={})
        result = handler.get(1)
        mock_http_get.assert_called_once_with(endpoint="groups/1")
        self.assertEqual(result["title"], "Group A")
        self.assertEqual(result["pk"], 1)

    @patch.object(GeonodeGroupsHandler, "http_get")
    def test_get_returns_none_on_missing(self, mock_http_get):
        """Ensure get returns None if http_get returns None."""
        mock_http_get.return_value = None
        handler = GeonodeGroupsHandler(env={})
        result = handler.get(999)
        self.assertIsNone(result)

    @patch.object(GeonodeGroupsHandler, "http_patch")
    def test_patch(self, mock_http_patch):
        """Ensure patch calls the correct endpoint with JSON content."""
        mock_http_patch.return_value = {"pk": 1, "title": "Updated Group"}
        handler = GeonodeGroupsHandler(env={})
        result = handler.patch(1, json_content={"title": "Updated Group"})
        mock_http_patch.assert_called_once_with(
            endpoint="groups/1/", json_content={"title": "Updated Group"}
        )
        self.assertEqual(result["title"], "Updated Group")

    @patch.object(GeonodeGroupsHandler, "http_post")
    def test_create_with_title(self, mock_http_post):
        """Ensure create with title sends the correct JSON payload."""
        mock_http_post.return_value = {"pk": 5, "title": "New Group"}
        handler = GeonodeGroupsHandler(env={})
        result = handler.create(
            title="New Group", name="new-group", description="A desc"
        )
        mock_http_post.assert_called_once_with(
            endpoint="groups",
            json={"title": "New Group", "description": "A desc", "name": "new-group"},
        )
        self.assertEqual(result["pk"], 5)

    @patch.object(GeonodeGroupsHandler, "http_post")
    def test_create_with_json_content(self, mock_http_post):
        """Ensure create with json_content bypasses individual fields."""
        mock_http_post.return_value = {"pk": 6, "title": "JSON Group"}
        handler = GeonodeGroupsHandler(env={})
        json_content = {"title": "JSON Group", "description": "from json"}
        result = handler.create(json_content=json_content)
        mock_http_post.assert_called_once_with(endpoint="groups", json=json_content)
        self.assertEqual(result["pk"], 6)

    @patch.object(GeonodeGroupsHandler, "http_delete")
    def test_delete(self, mock_http_delete):
        """Ensure delete calls the correct endpoint."""
        mock_http_delete.return_value = {}
        handler = GeonodeGroupsHandler(env={})
        handler.delete(pk=3)
        mock_http_delete.assert_called_once_with(endpoint="groups/3/")

    @patch.object(GeonodeGroupsHandler, "http_delete")
    def test_delete_range(self, mock_http_delete):
        """Ensure range delete only calls group endpoint for each pk in range."""
        mock_http_delete.return_value = {}
        handler = GeonodeGroupsHandler(env={})
        for pk in range(1, 4):
            handler.delete(pk=pk)
        calls = [c.kwargs["endpoint"] for c in mock_http_delete.call_args_list]
        self.assertEqual(calls, ["groups/1/", "groups/2/", "groups/3/"])


if __name__ == "__main__":
    unittest.main()
