import unittest
from unittest.mock import patch

from geonoderest.users import GeonodeUsersHandler
from geonoderest.exceptions import GeoNodeRestException


class TestGeonodeUsersHandlerTransferResources(unittest.TestCase):

    @patch.object(GeonodeUsersHandler, "http_post")
    def test_transfer_resources_subset(self, mock_http_post):
        """Ensure the modern payload carries the subset and no retry happens."""
        mock_http_post.return_value = "Resources transfered successfully"
        handler = GeonodeUsersHandler(env={})
        result = handler.transfer_resources(pk=3, new_owner=7, resources=[11, 12])
        mock_http_post.assert_called_once_with(
            endpoint="users/3/transfer_resources",
            json={"newOwner": 7, "currentOwner": 3, "resources": [11, 12]},
        )
        self.assertEqual(result, "Resources transfered successfully")

    @patch.object(GeonodeUsersHandler, "http_post")
    def test_transfer_all_resources_sends_an_empty_subset(self, mock_http_post):
        """GeoNode 5 raises a TypeError if `resources` is missing from a JSON body."""
        mock_http_post.return_value = "Resources transfered successfully"
        handler = GeonodeUsersHandler(env={})
        handler.transfer_resources(pk=3, new_owner=7)
        self.assertEqual(mock_http_post.call_args.kwargs["json"]["resources"], [])

    @patch.object(GeonodeUsersHandler, "http_post")
    def test_transfer_all_resources_falls_back_to_the_geonode_44_payload(
        self, mock_http_post
    ):
        """GeoNode 4.4 does not know newOwner, so the legacy `owner` is tried after it."""
        mock_http_post.side_effect = [None, "Resources transfered successfully"]
        handler = GeonodeUsersHandler(env={})
        result = handler.transfer_resources(pk=3, new_owner=7)
        self.assertEqual(mock_http_post.call_count, 2)
        self.assertEqual(
            mock_http_post.call_args.kwargs,
            {"endpoint": "users/3/transfer_resources", "json": {"owner": 7}},
        )
        self.assertEqual(result, "Resources transfered successfully")

    @patch.object(GeonodeUsersHandler, "http_post")
    def test_transfer_of_a_subset_is_not_retried_as_a_whole_account_transfer(
        self, mock_http_post
    ):
        """The GeoNode 4.4 payload would move every resource, which was not asked for."""
        mock_http_post.return_value = None
        handler = GeonodeUsersHandler(env={})
        with self.assertRaises(GeoNodeRestException):
            handler.transfer_resources(pk=3, new_owner=7, resources=[11])
        mock_http_post.assert_called_once()


if __name__ == "__main__":
    unittest.main()
