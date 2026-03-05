import unittest
from unittest.mock import patch, Mock

import requests
import urllib3

from geonoderest.apiconf import GeonodeApiConf
from geonoderest.rest import GeonodeRest
from geonoderest.exceptions import GeoNodeRestException


def _make_rest():
    conf = GeonodeApiConf(
        url="http://example.com/api/v2/",
        auth_basic="dGVzdDp0ZXN0",
        verify=True,
    )
    return GeonodeRest(env=conf)


def _mock_response(status_code=200, json_data=None, text=""):
    response = Mock(spec=requests.Response)
    response.status_code = status_code
    response.reason = "OK"
    response.text = text
    response.url = "http://example.com/api/v2/test"
    response.json.return_value = json_data or {}
    response.raise_for_status.return_value = None
    return response


# ---------------------------------------------------------------------------
# HTTP Error formatting
# ---------------------------------------------------------------------------


class GeonodeRestHttpErrorTests(unittest.TestCase):
    def setUp(self):
        self.rest = _make_rest()

    @patch("geonoderest.rest.requests.post")
    def test_http_post_raises_exception_with_json_detail(self, mock_post):
        resp = _mock_response(400, json_data={"detail": "username already taken"})
        resp.reason = "Bad Request"
        resp.raise_for_status.side_effect = requests.exceptions.HTTPError(response=resp)
        mock_post.return_value = resp

        with self.assertRaises(GeoNodeRestException) as exc:
            self.rest.http_post("users", json={"name": "x"})
        self.assertIn("username already taken", str(exc.exception))
        self.assertIn("400", str(exc.exception))

    @patch("geonoderest.rest.requests.get")
    def test_http_get_raises_exception_with_text_body(self, mock_get):
        resp = _mock_response(404, text="Resource not found")
        resp.reason = "Not Found"
        resp.json.side_effect = ValueError()
        resp.raise_for_status.side_effect = requests.exceptions.HTTPError(response=resp)
        mock_get.return_value = resp

        with self.assertRaises(GeoNodeRestException) as exc:
            self.rest.http_get("resources/11")
        self.assertIn("404", str(exc.exception))
        self.assertIn("Resource not found", str(exc.exception))

    @patch("geonoderest.rest.requests.patch")
    def test_patch_422_with_errors_list(self, mock_patch):
        resp = _mock_response(422, json_data={"errors": ["field required"]})
        resp.reason = "Unprocessable Entity"
        resp.raise_for_status.side_effect = requests.exceptions.HTTPError(response=resp)
        mock_patch.return_value = resp

        with self.assertRaises(GeoNodeRestException) as cm:
            self.rest.http_patch("resources/1/", json_content={"bad": "data"})
        self.assertIn("field required", str(cm.exception))

    @patch("geonoderest.rest.requests.delete")
    def test_delete_403_raises(self, mock_delete):
        resp = _mock_response(403, json_data={"detail": "not allowed"})
        resp.reason = "Forbidden"
        resp.raise_for_status.side_effect = requests.exceptions.HTTPError(response=resp)
        mock_delete.return_value = resp

        with self.assertRaises(GeoNodeRestException):
            self.rest.http_delete("resources/1/")


# ---------------------------------------------------------------------------
# Successful HTTP paths
# ---------------------------------------------------------------------------


class TestHttpSuccess(unittest.TestCase):
    def setUp(self):
        self.rest = _make_rest()

    @patch("geonoderest.rest.requests.get")
    def test_http_get_returns_json(self, mock_get):
        mock_get.return_value = _mock_response(json_data={"datasets": [{"pk": 1}]})
        result = self.rest.http_get("datasets/")
        self.assertEqual(result["datasets"][0]["pk"], 1)

    @patch("geonoderest.rest.requests.post")
    def test_http_post_returns_json(self, mock_post):
        mock_post.return_value = _mock_response(json_data={"execution_id": "abc-123"})
        result = self.rest.http_post("uploads/upload", data={"key": "val"})
        self.assertEqual(result["execution_id"], "abc-123")

    @patch("geonoderest.rest.requests.patch")
    def test_http_patch_returns_json(self, mock_patch):
        mock_patch.return_value = _mock_response(json_data={"pk": 5, "title": "new"})
        result = self.rest.http_patch("datasets/5/", json_content={"title": "new"})
        self.assertEqual(result["title"], "new")

    @patch("geonoderest.rest.requests.delete")
    def test_http_delete_204_returns_empty_dict(self, mock_delete):
        resp = _mock_response(status_code=204)
        mock_delete.return_value = resp
        result = self.rest.http_delete("datasets/5/")
        self.assertEqual(result, {})

    @patch("geonoderest.rest.requests.delete")
    def test_http_delete_200_returns_json(self, mock_delete):
        mock_delete.return_value = _mock_response(json_data={"deleted": True})
        result = self.rest.http_delete("datasets/5/")
        self.assertTrue(result["deleted"])

    @patch("geonoderest.rest.requests.get")
    def test_http_get_download_returns_response_object(self, mock_get):
        resp = _mock_response(text="<xml/>")
        mock_get.return_value = resp
        result = self.rest.http_get_download("http://example.com/metadata")
        self.assertIs(result, resp)


# ---------------------------------------------------------------------------
# Network-level exceptions
# ---------------------------------------------------------------------------


class TestNetworkExceptionHandling(unittest.TestCase):
    def setUp(self):
        self.rest = _make_rest()

    @patch("geonoderest.rest.requests.get")
    def test_connection_error_raises_geonode_exception(self, mock_get):
        mock_get.side_effect = requests.exceptions.ConnectionError()
        with self.assertRaises(GeoNodeRestException) as cm:
            self.rest.http_get("datasets/")
        self.assertIn("connection error", str(cm.exception).lower())

    @patch("geonoderest.rest.requests.get")
    def test_max_retry_error_raises_geonode_exception(self, mock_get):
        mock_get.side_effect = urllib3.exceptions.MaxRetryError(pool=Mock(), url="x")
        with self.assertRaises(GeoNodeRestException) as cm:
            self.rest.http_get("datasets/")
        self.assertIn("max retries", str(cm.exception).lower())

    @patch("geonoderest.rest.requests.get")
    def test_connection_refused_raises_geonode_exception(self, mock_get):
        mock_get.side_effect = ConnectionRefusedError()
        with self.assertRaises(GeoNodeRestException) as cm:
            self.rest.http_get("datasets/")
        self.assertIn("connection refused", str(cm.exception).lower())

    @patch("geonoderest.rest.requests.post")
    def test_post_connection_error_raises_geonode_exception(self, mock_post):
        mock_post.side_effect = requests.exceptions.ConnectionError()
        with self.assertRaises(GeoNodeRestException):
            self.rest.http_post("datasets/")


# ---------------------------------------------------------------------------
# Timeout forwarded to requests
# ---------------------------------------------------------------------------


class TestTimeoutForwarded(unittest.TestCase):
    def setUp(self):
        self.rest = _make_rest()

    @patch("geonoderest.rest.requests.get")
    def test_http_get_passes_default_timeout(self, mock_get):
        mock_get.return_value = _mock_response(json_data={})
        self.rest.http_get("datasets/")
        _, kwargs = mock_get.call_args
        self.assertEqual(kwargs["timeout"], 60)

    @patch("geonoderest.rest.requests.get")
    def test_http_get_passes_custom_timeout(self, mock_get):
        mock_get.return_value = _mock_response(json_data={})
        self.rest.http_get("datasets/", timeout=120)
        _, kwargs = mock_get.call_args
        self.assertEqual(kwargs["timeout"], 120)

    @patch("geonoderest.rest.requests.post")
    def test_http_post_passes_default_timeout(self, mock_post):
        mock_post.return_value = _mock_response(json_data={})
        self.rest.http_post("uploads/upload")
        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs["timeout"], 60)

    @patch("geonoderest.rest.requests.patch")
    def test_http_patch_passes_default_timeout(self, mock_patch):
        mock_patch.return_value = _mock_response(json_data={})
        self.rest.http_patch("datasets/1/")
        _, kwargs = mock_patch.call_args
        self.assertEqual(kwargs["timeout"], 60)

    @patch("geonoderest.rest.requests.delete")
    def test_http_delete_passes_default_timeout(self, mock_delete):
        mock_delete.return_value = _mock_response(json_data={})
        self.rest.http_delete("datasets/1/")
        _, kwargs = mock_delete.call_args
        self.assertEqual(kwargs["timeout"], 60)


if __name__ == "__main__":
    unittest.main()
