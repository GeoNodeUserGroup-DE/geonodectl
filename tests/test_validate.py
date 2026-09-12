import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import requests

from geonoderest.datasets import GeonodeDatasetsHandler
from geonoderest.resources import GeonodeResourceHandler
from geonoderest.validate import (
    SchemaLoadError,
    build_validator,
    collect_errors,
    load_schema,
)

BASELINE_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["title"],
    "properties": {
        "title": {"type": "string", "minLength": 3},
        "doi": {"type": ["string", "null"], "pattern": r"^10\.\d{4,9}/\S+$"},
    },
    # a published DOI requires a real license
    "if": {"required": ["doi"], "properties": {"doi": {"type": "string"}}},
    "then": {"required": ["license"]},
}


def _write(tmpdir, name, obj):
    path = os.path.join(tmpdir, name)
    with open(path, "w") as f:
        json.dump(obj, f)
    return path


def _validator(tmpdir, schema=None):
    path = _write(tmpdir, "schema.json", schema or BASELINE_SCHEMA)
    return build_validator(load_schema(path), path)


def _serve(pages):
    """fake requests.get, answering each url from ``pages``

    Keys are urls, values the parsed json to hand back; an unknown url answers
    404 the way a real web server would.
    """

    def get(url, **kwargs):
        r = MagicMock()
        if url not in pages:
            r.raise_for_status.side_effect = requests.exceptions.HTTPError("404")
            return r
        r.raise_for_status.return_value = None
        r.json.return_value = pages[url]
        return r

    return get


class TestLoadSchema(unittest.TestCase):
    def test_missing_file(self):
        with self.assertRaises(SchemaLoadError):
            load_schema("/nonexistent/nope.json")

    def test_malformed_json(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "bad.json")
            with open(path, "w") as f:
                f.write("{not json")
            with self.assertRaises(SchemaLoadError):
                load_schema(path)

    def test_invalid_schema_is_rejected(self):
        """a syntactically fine file that is not a valid JSON Schema"""
        with tempfile.TemporaryDirectory() as d:
            path = _write(d, "schema.json", {"type": "not-a-real-type"})
            with self.assertRaises(SchemaLoadError):
                build_validator(load_schema(path), path)

    def test_non_utf8_file(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "binary.json")
            with open(path, "wb") as f:
                f.write(b'\xff\xfe{"type":"object"}')
            with self.assertRaises(SchemaLoadError):
                load_schema(path)


class TestCollectErrors(unittest.TestCase):
    def test_valid_object_has_no_errors(self):
        with tempfile.TemporaryDirectory() as d:
            v = _validator(d)
            self.assertEqual(collect_errors(v, {"title": "a good title"}), [])

    def test_reports_path_and_keyword(self):
        with tempfile.TemporaryDirectory() as d:
            v = _validator(d)
            errors = collect_errors(v, {"title": "x"})
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]["path"], "$.title")
        self.assertEqual(errors[0]["keyword"], "minLength")

    def test_reports_every_violation_not_just_the_first(self):
        with tempfile.TemporaryDirectory() as d:
            v = _validator(d)
            errors = collect_errors(v, {"title": "x", "doi": "not-a-doi"})
        paths = sorted(e["path"] for e in errors)
        self.assertEqual(paths, ["$", "$.doi", "$.title"])

    def test_conditional_fires_when_doi_is_a_string(self):
        """if/then: a DOI-bearing object must carry a license"""
        with tempfile.TemporaryDirectory() as d:
            v = _validator(d)
            errors = collect_errors(v, {"title": "a good title", "doi": "10.1234/abc"})
        self.assertEqual([e["keyword"] for e in errors], ["required"])
        self.assertIn("license", errors[0]["message"])

    def test_conditional_does_not_fire_when_doi_is_null(self):
        """GeoNode always emits the doi key, null when unset — must not match"""
        with tempfile.TemporaryDirectory() as d:
            v = _validator(d)
            errors = collect_errors(v, {"title": "a good title", "doi": None})
        self.assertEqual(errors, [])

    def test_local_ref_to_sibling_file_resolves(self):
        with tempfile.TemporaryDirectory() as d:
            _write(d, "common.json", BASELINE_SCHEMA)
            path = _write(
                d,
                "dataset.json",
                {
                    "$schema": "https://json-schema.org/draft/2020-12/schema",
                    "allOf": [{"$ref": "common.json"}],
                },
            )
            v = build_validator(load_schema(path), path)
            errors = collect_errors(v, {"title": "x"})
        # the violation comes from the referenced file, not the root schema
        self.assertEqual(errors[0]["path"], "$.title")
        self.assertEqual(errors[0]["keyword"], "minLength")

    def test_remote_ref_is_not_fetched(self):
        """a remote $ref must surface as SchemaLoadError, not a raw traceback"""
        with tempfile.TemporaryDirectory() as d:
            path = _write(
                d,
                "schema.json",
                {
                    "$schema": "https://json-schema.org/draft/2020-12/schema",
                    "allOf": [{"$ref": "https://example.org/schema.json"}],
                },
            )
            v = build_validator(load_schema(path), path)
            with self.assertRaises(SchemaLoadError):
                collect_errors(v, {"title": "x"})

    def test_missing_sibling_ref_raises_schema_load_error(self):
        with tempfile.TemporaryDirectory() as d:
            path = _write(
                d,
                "schema.json",
                {
                    "$schema": "https://json-schema.org/draft/2020-12/schema",
                    "allOf": [{"$ref": "does-not-exist.json"}],
                },
            )
            v = build_validator(load_schema(path), path)
            with self.assertRaises(SchemaLoadError):
                collect_errors(v, {"title": "x"})

    def test_ref_resolves_under_a_path_containing_a_space(self):
        """Path.as_uri() percent-encodes; the retrieve callback must decode"""
        with tempfile.TemporaryDirectory() as d:
            sub = os.path.join(d, "my schemas")
            os.makedirs(sub)
            _write(sub, "common.json", BASELINE_SCHEMA)
            path = _write(
                sub,
                "dataset.json",
                {
                    "$schema": "https://json-schema.org/draft/2020-12/schema",
                    "allOf": [{"$ref": "common.json"}],
                },
            )
            v = build_validator(load_schema(path), path)
            errors = collect_errors(v, {"title": "x"})
        self.assertEqual(errors[0]["path"], "$.title")


class TestRemoteSchema(unittest.TestCase):
    """a schema given as --json_schema_url, see #159"""

    SCHEMA_URL = "https://example.org/schemas/dataset.json"
    COMMON_URL = "https://example.org/schemas/common.json"

    @patch("geonoderest.jsonsource.requests.get")
    def test_loads_a_schema_from_a_url(self, mock_get):
        mock_get.side_effect = _serve({self.SCHEMA_URL: BASELINE_SCHEMA})
        schema = load_schema(self.SCHEMA_URL)
        self.assertEqual(schema, BASELINE_SCHEMA)

    @patch("geonoderest.jsonsource.requests.get")
    def test_unreachable_url_raises_schema_load_error(self, mock_get):
        mock_get.side_effect = _serve({})
        with self.assertRaises(SchemaLoadError):
            load_schema(self.SCHEMA_URL)

    @patch("geonoderest.jsonsource.requests.get")
    def test_validates_against_a_remote_schema(self, mock_get):
        mock_get.side_effect = _serve({self.SCHEMA_URL: BASELINE_SCHEMA})
        v = build_validator(load_schema(self.SCHEMA_URL), self.SCHEMA_URL)
        self.assertEqual(collect_errors(v, {"title": "a good title"}), [])
        errors = collect_errors(v, {"title": "x"})
        self.assertEqual(errors[0]["path"], "$.title")

    @patch("geonoderest.jsonsource.requests.get")
    def test_relative_ref_resolves_against_the_schema_url(self, mock_get):
        """a hosted schema set must work the same way a local directory does"""
        root = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "allOf": [{"$ref": "common.json"}],
        }
        mock_get.side_effect = _serve(
            {self.SCHEMA_URL: root, self.COMMON_URL: BASELINE_SCHEMA}
        )
        v = build_validator(load_schema(self.SCHEMA_URL), self.SCHEMA_URL)
        errors = collect_errors(v, {"title": "x"})
        # the violation comes from the referenced url, not the root schema
        self.assertEqual(errors[0]["path"], "$.title")
        self.assertEqual(errors[0]["keyword"], "minLength")

    @patch("geonoderest.jsonsource.requests.get")
    def test_unresolvable_remote_ref_raises_schema_load_error(self, mock_get):
        root = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "allOf": [{"$ref": "does-not-exist.json"}],
        }
        mock_get.side_effect = _serve({self.SCHEMA_URL: root})
        v = build_validator(load_schema(self.SCHEMA_URL), self.SCHEMA_URL)
        with self.assertRaises(SchemaLoadError):
            collect_errors(v, {"title": "x"})

    @patch("geonoderest.jsonsource.requests.get")
    def test_a_remote_ref_is_fetched_only_once(self, mock_get):
        """Registry is immutable, so without a cache each object refetches it"""
        root = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "allOf": [{"$ref": "common.json"}],
        }
        mock_get.side_effect = _serve(
            {self.SCHEMA_URL: root, self.COMMON_URL: BASELINE_SCHEMA}
        )
        v = build_validator(load_schema(self.SCHEMA_URL), self.SCHEMA_URL)
        for _ in range(5):
            collect_errors(v, {"title": "a good title"})
        # one for the root schema, one for common.json, and nothing more
        self.assertEqual(mock_get.call_count, 2)

    @patch("geonoderest.jsonsource.requests.get")
    def test_remote_schema_cannot_read_the_local_filesystem(self, mock_get):
        """a file:// ref in a hosted schema would leak the file into the report"""
        with tempfile.TemporaryDirectory() as d:
            secret = _write(
                d, "secret.json", {"properties": {"title": {"const": "s3cr3t"}}}
            )
            root = {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "allOf": [{"$ref": Path(secret).as_uri()}],
            }
            mock_get.side_effect = _serve({self.SCHEMA_URL: root})
            v = build_validator(load_schema(self.SCHEMA_URL), self.SCHEMA_URL)
            with self.assertRaises(SchemaLoadError):
                collect_errors(v, {"title": "whatever"})

    @patch("geonoderest.jsonsource.requests.get")
    def test_local_schema_still_refuses_a_remote_ref(self, mock_get):
        """reading a schema from disk must not make the tool hit the network"""
        with tempfile.TemporaryDirectory() as d:
            path = _write(
                d,
                "schema.json",
                {
                    "$schema": "https://json-schema.org/draft/2020-12/schema",
                    "allOf": [{"$ref": "https://example.org/schemas/common.json"}],
                },
            )
            v = build_validator(load_schema(path), path)
            with self.assertRaises(SchemaLoadError):
                collect_errors(v, {"title": "x"})
        mock_get.assert_not_called()


class TestValidateLibraryMethod(unittest.TestCase):
    """validate() must not print or exit — it is the library entry point (#69)"""

    @patch.object(GeonodeDatasetsHandler, "http_get")
    def test_returns_empty_list_for_valid_object(self, mock_http_get):
        mock_http_get.return_value = {"dataset": {"title": "a good title"}}
        with tempfile.TemporaryDirectory() as d:
            v = _validator(d)
            result = GeonodeDatasetsHandler(env={}).validate(pk=1, validator=v)
        self.assertEqual(result, [])

    @patch.object(GeonodeDatasetsHandler, "http_get")
    def test_returns_violations_for_invalid_object(self, mock_http_get):
        mock_http_get.return_value = {"dataset": {"title": "x"}}
        with tempfile.TemporaryDirectory() as d:
            v = _validator(d)
            result = GeonodeDatasetsHandler(env={}).validate(pk=1, validator=v)
        self.assertEqual(len(result), 1)

    @patch.object(GeonodeDatasetsHandler, "http_get", return_value=None)
    def test_returns_none_when_object_cannot_be_fetched(self, _):
        with tempfile.TemporaryDirectory() as d:
            v = _validator(d)
            result = GeonodeDatasetsHandler(env={}).validate(pk=999, validator=v)
        self.assertIsNone(result)


class TestCmdValidate(unittest.TestCase):
    def _run(self, handler, pk, schema_path, **kwargs):
        """run cmd_validate and return the exit code it reports"""
        return handler.cmd_validate(pk=pk, json_schema=schema_path, **kwargs)

    @patch.object(GeonodeDatasetsHandler, "http_get")
    def test_exit_0_when_valid(self, mock_http_get):
        mock_http_get.return_value = {"dataset": {"title": "a good title"}}
        with tempfile.TemporaryDirectory() as d:
            path = _write(d, "schema.json", BASELINE_SCHEMA)
            code = self._run(GeonodeDatasetsHandler(env={}), "1", path, json=False)
        self.assertEqual(code, 0)

    @patch.object(GeonodeDatasetsHandler, "http_get")
    def test_exit_1_when_invalid(self, mock_http_get):
        mock_http_get.return_value = {"dataset": {"title": "x"}}
        with tempfile.TemporaryDirectory() as d:
            path = _write(d, "schema.json", BASELINE_SCHEMA)
            code = self._run(GeonodeDatasetsHandler(env={}), "1", path, json=False)
        self.assertEqual(code, 1)

    @patch.object(GeonodeDatasetsHandler, "http_get")
    def test_exit_2_when_schema_file_missing(self, _):
        with self.assertLogs(level="ERROR"):
            code = self._run(
                GeonodeDatasetsHandler(env={}),
                "1",
                "/nonexistent/nope.json",
                json=False,
            )
        self.assertEqual(code, 2)

    @patch.object(GeonodeDatasetsHandler, "http_get")
    def test_exit_2_when_schema_is_invalid(self, _):
        with tempfile.TemporaryDirectory() as d:
            path = _write(d, "schema.json", {"type": "not-a-real-type"})
            with self.assertLogs(level="ERROR"):
                code = self._run(GeonodeDatasetsHandler(env={}), "1", path, json=False)
        self.assertEqual(code, 2)

    @patch.object(GeonodeDatasetsHandler, "http_get")
    def test_exit_2_when_a_ref_cannot_be_resolved(self, mock_http_get):
        """an unusable schema must not look like invalid metadata (exit 1)"""
        mock_http_get.return_value = {"dataset": {"title": "a good title"}}
        with tempfile.TemporaryDirectory() as d:
            path = _write(
                d,
                "schema.json",
                {
                    "$schema": "https://json-schema.org/draft/2020-12/schema",
                    "allOf": [{"$ref": "does-not-exist.json"}],
                },
            )
            with self.assertLogs(level="ERROR"):
                code = self._run(GeonodeDatasetsHandler(env={}), "1", path, json=False)
        self.assertEqual(code, 2)

    @patch.object(GeonodeDatasetsHandler, "http_get", return_value=None)
    def test_exit_1_when_object_unreachable(self, _):
        """a 404 is a failed operation (1), not a usage error (2) - see #151"""
        with tempfile.TemporaryDirectory() as d:
            path = _write(d, "schema.json", BASELINE_SCHEMA)
            with self.assertLogs(level="ERROR"):
                code = self._run(
                    GeonodeDatasetsHandler(env={}), "999", path, json=False
                )
        self.assertEqual(code, 1)

    @patch.object(GeonodeDatasetsHandler, "http_get")
    def test_exit_2_on_an_invalid_pk(self, _):
        with tempfile.TemporaryDirectory() as d:
            path = _write(d, "schema.json", BASELINE_SCHEMA)
            with self.assertLogs(level="ERROR"):
                code = self._run(
                    GeonodeDatasetsHandler(env={}), "abc", path, json=False
                )
        self.assertEqual(code, 2)

    @patch.object(GeonodeDatasetsHandler, "http_get")
    def test_pk_range_validates_each_pk(self, mock_http_get):
        mock_http_get.return_value = {"dataset": {"title": "a good title"}}
        with tempfile.TemporaryDirectory() as d:
            path = _write(d, "schema.json", BASELINE_SCHEMA)
            code = self._run(GeonodeDatasetsHandler(env={}), "1-5", path, json=False)
        self.assertEqual(code, 0)
        self.assertEqual(mock_http_get.call_count, 5)

    @patch.object(GeonodeDatasetsHandler, "http_get")
    def test_pk_range_exits_1_if_any_object_is_invalid(self, mock_http_get):
        mock_http_get.side_effect = [
            {"dataset": {"title": "a good title"}},
            {"dataset": {"title": "x"}},
            {"dataset": {"title": "another good title"}},
        ]
        with tempfile.TemporaryDirectory() as d:
            path = _write(d, "schema.json", BASELINE_SCHEMA)
            code = self._run(GeonodeDatasetsHandler(env={}), "1,2,3", path, json=False)
        self.assertEqual(code, 1)

    @patch.object(GeonodeDatasetsHandler, "http_get")
    def test_raw_emits_machine_readable_report(self, mock_http_get):
        mock_http_get.return_value = {"dataset": {"title": "x"}}
        with tempfile.TemporaryDirectory() as d:
            path = _write(d, "schema.json", BASELINE_SCHEMA)
            with patch("geonoderest.resources.print_json") as mock_print:
                self._run(GeonodeDatasetsHandler(env={}), "1", path, json=True)
        report = mock_print.call_args.args[0]
        self.assertEqual(report[0]["pk"], 1)
        self.assertFalse(report[0]["valid"])
        self.assertEqual(report[0]["errors"][0]["path"], "$.title")

    @patch.object(GeonodeDatasetsHandler, "http_get")
    @patch("geonoderest.jsonsource.requests.get")
    def test_exit_0_with_a_schema_url(self, mock_get, mock_http_get):
        """--json_schema takes a url just as well as a path"""
        url = "https://example.org/schemas/dataset.json"
        mock_get.side_effect = _serve({url: BASELINE_SCHEMA})
        mock_http_get.return_value = {"dataset": {"title": "a good title"}}
        code = self._run(GeonodeDatasetsHandler(env={}), "1", url, json=False)
        self.assertEqual(code, 0)

    @patch.object(GeonodeDatasetsHandler, "http_get")
    @patch("geonoderest.jsonsource.requests.get")
    def test_exit_1_with_a_schema_url(self, mock_get, mock_http_get):
        url = "https://example.org/schemas/dataset.json"
        mock_get.side_effect = _serve({url: BASELINE_SCHEMA})
        mock_http_get.return_value = {"dataset": {"title": "x"}}
        code = self._run(GeonodeDatasetsHandler(env={}), "1", url, json=False)
        self.assertEqual(code, 1)

    @patch.object(GeonodeDatasetsHandler, "http_get")
    @patch("geonoderest.jsonsource.requests.get")
    def test_exit_2_when_the_schema_url_is_unreachable(self, mock_get, _):
        mock_get.side_effect = _serve({})
        with self.assertLogs(level="ERROR"):
            code = self._run(
                GeonodeDatasetsHandler(env={}),
                "1",
                "https://example.org/schemas/gone.json",
                json=False,
            )
        self.assertEqual(code, 2)

    @patch.object(GeonodeDatasetsHandler, "http_get")
    def test_exit_2_when_no_schema_given_at_all(self, _):
        """argparse enforces this, the handler must not traceback either"""
        with self.assertLogs(level="ERROR"):
            code = self._run(GeonodeDatasetsHandler(env={}), "1", None, json=False)
        self.assertEqual(code, 2)

    @patch.object(GeonodeResourceHandler, "http_get")
    def test_available_on_resource_handler(self, mock_http_get):
        """the verb is shared by resources and all four resource types"""
        mock_http_get.return_value = {"resource": {"title": "a good title"}}
        with tempfile.TemporaryDirectory() as d:
            path = _write(d, "schema.json", BASELINE_SCHEMA)
            code = self._run(GeonodeResourceHandler(env={}), "1", path, json=False)
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
