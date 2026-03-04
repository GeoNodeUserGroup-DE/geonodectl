import unittest
from unittest.mock import patch, Mock

import requests

from geonoderest.apiconf import GeonodeApiConf
from geonoderest.rest import GeonodeRest
from geonoderest.exceptions import GeoNodeRestException


class GeonodeRestHttpErrorTests(unittest.TestCase):
    def setUp(self):
        self.conf = GeonodeApiConf(
            url="http://example.com/api/v2/",
            auth_basic="dGVzdDp0ZXN0",
            verify=True,
        )
        self.rest = GeonodeRest(env=self.conf)

    @patch("geonoderest.rest.requests.post")
    def test_http_post_raises_exception_with_json_detail(self, mock_post):
        response = Mock(spec=requests.Response)
        response.status_code = 400
        response.reason = "Bad Request"
        response.text = '{"detail": "username already taken"}'
        response.json.return_value = {"detail": "username already taken"}
        response.url = "http://example.com/api/v2/users"
        http_error = requests.exceptions.HTTPError(response=response)
        response.raise_for_status.side_effect = http_error
        mock_post.return_value = response

        with self.assertRaises(GeoNodeRestException) as exc:
            self.rest.http_post("users", json={})

        self.assertIn("username already taken", str(exc.exception))
        self.assertIn("400", str(exc.exception))

    @patch("geonoderest.rest.requests.get")
    def test_http_get_raises_exception_with_text_body(self, mock_get):
        response = Mock(spec=requests.Response)
        response.status_code = 404
        response.reason = "Not Found"
        response.text = "Resource not found"
        response.json.side_effect = ValueError()
        response.url = "http://example.com/api/v2/resources/11"
        http_error = requests.exceptions.HTTPError(response=response)
        response.raise_for_status.side_effect = http_error
        mock_get.return_value = response

        with self.assertRaises(GeoNodeRestException) as exc:
            self.rest.http_get("resources/11")

        message = str(exc.exception)
        self.assertIn("404", message)
        self.assertIn("Resource not found", message)


if __name__ == "__main__":
    unittest.main()
