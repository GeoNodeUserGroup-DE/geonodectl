import json
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import requests

from geonoderest.jsonsource import (
    DEFAULT_TIMEOUT,
    JsonSourceError,
    fetch_json_url,
    is_http_url,
    load_json,
    load_json_file,
    load_json_source,
    load_json_string,
)

URL = "https://example.org/meta.json"


def _write(tmpdir, name, obj):
    path = os.path.join(tmpdir, name)
    with open(path, "w") as f:
        json.dump(obj, f)
    return path


def _response(payload=None, status_error=None, json_error=False):
    """a stand-in for requests.Response covering the three ways a fetch fails"""
    r = MagicMock()
    if status_error is not None:
        r.raise_for_status.side_effect = status_error
    else:
        r.raise_for_status.return_value = None
    if json_error:
        r.json.side_effect = json.decoder.JSONDecodeError("boom", "<html>", 0)
    else:
        r.json.return_value = payload
    return r


class TestIsHttpUrl(unittest.TestCase):
    def test_http_and_https_are_urls(self):
        self.assertTrue(is_http_url("http://example.org/a.json"))
        self.assertTrue(is_http_url("https://example.org/a.json"))

    def test_paths_are_not_urls(self):
        for value in ("./a.json", "/tmp/a.json", "a.json", "C:/a.json"):
            self.assertFalse(is_http_url(value), value)

    def test_other_schemes_are_not_urls(self):
        """file:// and ftp:// must not be mistaken for something we can fetch"""
        self.assertFalse(is_http_url("file:///tmp/a.json"))
        self.assertFalse(is_http_url("ftp://example.org/a.json"))


class TestLoadJsonFile(unittest.TestCase):
    def test_reads_and_parses(self):
        with tempfile.TemporaryDirectory() as d:
            path = _write(d, "a.json", {"title": "hello"})
            self.assertEqual(load_json_file(path), {"title": "hello"})

    def test_missing_file(self):
        with self.assertRaises(JsonSourceError):
            load_json_file("/nonexistent/nope.json")

    def test_directory(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(JsonSourceError):
                load_json_file(d)

    def test_malformed_json(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "bad.json")
            with open(path, "w") as f:
                f.write("{not json")
            with self.assertRaises(JsonSourceError):
                load_json_file(path)

    def test_non_utf8_file(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "binary.json")
            with open(path, "wb") as f:
                f.write(b'\xff\xfe{"title":"hello"}')
            with self.assertRaises(JsonSourceError):
                load_json_file(path)


class TestLoadJsonString(unittest.TestCase):
    def test_parses(self):
        self.assertEqual(load_json_string('{"title": "hello"}'), {"title": "hello"})

    def test_malformed(self):
        with self.assertRaises(JsonSourceError):
            load_json_string("{not json")


class TestFetchJsonUrl(unittest.TestCase):
    @patch("geonoderest.jsonsource.requests.get")
    def test_returns_parsed_payload(self, mock_get):
        mock_get.return_value = _response({"title": "hello"})
        self.assertEqual(fetch_json_url(URL), {"title": "hello"})

    @patch("geonoderest.jsonsource.requests.get")
    def test_sends_a_timeout(self, mock_get):
        """a patch run must not hang forever on an unresponsive host"""
        mock_get.return_value = _response({})
        fetch_json_url(URL)
        self.assertEqual(mock_get.call_args.kwargs["timeout"], DEFAULT_TIMEOUT)

    @patch("geonoderest.jsonsource.requests.get")
    def test_timeout_is_configurable(self, mock_get):
        mock_get.return_value = _response({})
        fetch_json_url(URL, timeout=5)
        self.assertEqual(mock_get.call_args.kwargs["timeout"], 5)

    @patch("geonoderest.jsonsource.requests.get")
    def test_does_not_send_credentials(self, mock_get):
        """the GeoNode basic auth must never leak to a third party host"""
        mock_get.return_value = _response({})
        fetch_json_url(URL)
        headers = mock_get.call_args.kwargs["headers"]
        self.assertNotIn("Authorization", headers)
        self.assertNotIn("auth", mock_get.call_args.kwargs)
        self.assertNotIn("cookies", mock_get.call_args.kwargs)

    @patch("geonoderest.jsonsource.requests.get")
    def test_http_error_status(self, mock_get):
        mock_get.return_value = _response(
            status_error=requests.exceptions.HTTPError("404 Not Found")
        )
        with self.assertRaises(JsonSourceError) as cm:
            fetch_json_url(URL)
        self.assertIn(URL, str(cm.exception))

    @patch("geonoderest.jsonsource.requests.get")
    def test_connection_error(self, mock_get):
        mock_get.side_effect = requests.exceptions.ConnectionError("no route to host")
        with self.assertRaises(JsonSourceError):
            fetch_json_url(URL)

    @patch("geonoderest.jsonsource.requests.get")
    def test_timeout_error(self, mock_get):
        mock_get.side_effect = requests.exceptions.Timeout()
        with self.assertRaises(JsonSourceError) as cm:
            fetch_json_url(URL, timeout=7)
        self.assertIn("7s", str(cm.exception))

    @patch("geonoderest.jsonsource.requests.get")
    def test_body_is_not_json(self, mock_get):
        """a login page served with 200 must not pass as a schema"""
        mock_get.return_value = _response(json_error=True)
        with self.assertRaises(JsonSourceError):
            fetch_json_url(URL)

    @patch("geonoderest.jsonsource.requests.get")
    def test_error_messages_name_what_is_being_read(self, mock_get):
        """validate reports 'schema', patch reports 'json'"""
        mock_get.side_effect = requests.exceptions.ConnectionError("nope")
        with self.assertRaises(JsonSourceError) as cm:
            fetch_json_url(URL, what="schema")
        self.assertIn("could not fetch schema from", str(cm.exception))


class TestLoadJson(unittest.TestCase):
    """one argument, either kind of source - the point of #159"""

    def test_a_path_is_read_from_disk(self):
        with tempfile.TemporaryDirectory() as d:
            path = _write(d, "a.json", {"from": "disk"})
            self.assertEqual(load_json(path), {"from": "disk"})

    @patch("geonoderest.jsonsource.requests.get")
    def test_a_url_is_fetched(self, mock_get):
        mock_get.return_value = _response({"from": "url"})
        self.assertEqual(load_json(URL), {"from": "url"})
        self.assertEqual(mock_get.call_args.args[0], URL)

    @patch("geonoderest.jsonsource.requests.get")
    def test_a_path_never_hits_the_network(self, mock_get):
        with tempfile.TemporaryDirectory() as d:
            path = _write(d, "a.json", {})
            load_json(path)
        mock_get.assert_not_called()

    def test_a_filename_that_merely_contains_http_is_a_path(self):
        """'http-export.json' has no scheme, so it must be read from disk"""
        with tempfile.TemporaryDirectory() as d:
            path = _write(d, "http-export.json", {"from": "disk"})
            self.assertEqual(load_json(path), {"from": "disk"})

    def test_what_reaches_the_file_error_message(self):
        with self.assertRaises(JsonSourceError) as cm:
            load_json("/nonexistent/nope.json", what="schema")
        self.assertIn("schema file not found", str(cm.exception))


class TestLoadJsonSource(unittest.TestCase):
    @patch("geonoderest.jsonsource.requests.get")
    def test_json_path_accepts_a_url(self, mock_get):
        mock_get.return_value = _response({"from": "url"})
        self.assertEqual(load_json_source(json_path=URL), {"from": "url"})

    def test_path_wins_over_fields(self):
        with tempfile.TemporaryDirectory() as d:
            path = _write(d, "a.json", {"from": "path"})
            result = load_json_source(json_path=path, fields='{"from": "fields"}')
        self.assertEqual(result, {"from": "path"})

    def test_fields_alone(self):
        self.assertEqual(
            load_json_source(fields='{"from": "fields"}'), {"from": "fields"}
        )

    def test_nothing_provided(self):
        with self.assertRaises(JsonSourceError):
            load_json_source()

    @patch("geonoderest.jsonsource.requests.get")
    def test_timeout_reaches_the_request(self, mock_get):
        mock_get.return_value = _response({})
        load_json_source(json_path=URL, timeout=11)
        self.assertEqual(mock_get.call_args.kwargs["timeout"], 11)


if __name__ == "__main__":
    unittest.main()
