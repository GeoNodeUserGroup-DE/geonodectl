import io
import json
import unittest
from contextlib import redirect_stdout
from copy import deepcopy
from typing import Any, Dict, List
from unittest.mock import MagicMock

from geonoderest.apiconf import GeonodeApiConf
from geonoderest.exceptions import GeoNodeRestException, MetadataFieldError
from geonoderest.exitcodes import EXIT_FAILED, EXIT_OK, EXIT_USAGE
from geonoderest.metadata import GeonodeMetadataHandler
from metadata_schema import INSTANCE, SCHEMA

ENV = GeonodeApiConf(
    url="https://example.org/api/v2/", auth_basic="dXNlcjpwYXNz", verify=True
)
UPDATED = (200, {"message": "The resource was updated successfully", "extraErrors": {}})


class FakeApi:
    """stands in for ``http_send``: serves the schema and instances, and records
    every write instead of performing it"""

    def __init__(self, instances=None, writes=None):
        self.instances = instances if instances is not None else {42: INSTANCE}
        self.writes = writes or {}
        self.sent = []
        self.schema_requests = 0

    def __call__(self, method, endpoint, json_content=None, params={}, accept=()):
        if endpoint == "metadata/schema":
            self.schema_requests += 1
            return 200, deepcopy(SCHEMA)
        pk = int(endpoint.rsplit("/", 1)[1])
        if method == "GET":
            if pk in self.instances:
                return 200, deepcopy(self.instances[pk])
            return 404, {"message": "The dataset was not found"}
        self.sent.append((method, pk, json_content))
        return self.writes.get(pk, UPDATED)


def _handler(api):
    handler = GeonodeMetadataHandler(env=ENV)
    handler.http_send = MagicMock(side_effect=api)
    return handler


def _run(method, *args, **kwargs):
    """call a cmd_* method, return its exit code and what it printed"""
    out = io.StringIO()
    with redirect_stdout(out):
        code = method(*args, **kwargs)
    return code, out.getvalue()


class TestSchemaAndGet(unittest.TestCase):
    def test_schema_is_fetched_once_per_language(self):
        api = FakeApi()
        handler = _handler(api)
        handler.schema()
        handler.schema()
        self.assertEqual(api.schema_requests, 1)
        handler.schema(lang="de")
        self.assertEqual(api.schema_requests, 2)

    def test_a_missing_api_means_geonode_older_than_5(self):
        handler = GeonodeMetadataHandler(env=ENV)
        handler.http_send = MagicMock(return_value=(404, {}))
        with self.assertRaises(GeoNodeRestException) as cm:
            handler.schema()
        self.assertIn("GeoNode 5", str(cm.exception))

    def test_a_missing_resource_is_not_a_missing_api(self):
        handler = _handler(FakeApi())
        with self.assertLogs(level="ERROR") as logs:
            self.assertIsNone(handler.get(999))
        self.assertIn("The dataset was not found", "\n".join(logs.output))

    def test_a_missing_instance_route_is_a_missing_api(self):
        """GeoNode 4 answers with django's html 404, which arrives as {}"""
        handler = GeonodeMetadataHandler(env=ENV)
        handler.http_send = MagicMock(return_value=(404, {}))
        with self.assertRaises(GeoNodeRestException):
            handler.get(42)

    def test_get_selected_fields(self):
        code, out = _run(_handler(FakeApi()).cmd_get, pk="42", select="title,language")
        self.assertEqual(code, EXIT_OK)
        self.assertEqual(json.loads(out), {"title": "a dataset", "language": "eng"})

    def test_get_unknown_field(self):
        with self.assertLogs(level="ERROR") as logs:
            code, _ = _run(_handler(FakeApi()).cmd_get, pk="42", select="titel")
        self.assertEqual(code, EXIT_USAGE)
        self.assertIn("did you mean title", "\n".join(logs.output))

    def test_get_takes_a_single_resource(self):
        with self.assertLogs(level="ERROR"):
            code, _ = _run(_handler(FakeApi()).cmd_get, pk="1-3")
        self.assertEqual(code, EXIT_USAGE)


class TestLookup(unittest.TestCase):
    def _handler(self, results):
        handler = _handler(FakeApi())
        response = MagicMock()
        response.json.return_value = {"results": results}
        handler.http_get_download = MagicMock(return_value=response)
        return handler

    def test_the_url_comes_from_the_schema(self):
        handler = self._handler([{"id": "c_89", "label": "acid soils"}])
        result = handler.lookup("tkeywords.AGROVOC", "soil")
        handler.http_get_download.assert_called_once_with(
            "https://example.org/api/v2/metadata/autocomplete/thesaurus/2/keywords",
            params={"q": "soil"},
        )
        self.assertEqual(result, [{"id": "c_89", "label": "acid soils"}])

    def test_plain_string_results_become_id_and_label(self):
        handler = self._handler(["crop modeling"])
        self.assertEqual(
            handler.lookup("hkeywords"),
            [{"id": "crop modeling", "label": "crop modeling"}],
        )

    def test_a_field_without_lookup_lists_those_with_one(self):
        handler = self._handler([])
        with self.assertRaises(MetadataFieldError) as cm:
            handler.lookup("title")
        self.assertIn("tkeywords.AGROVOC", str(cm.exception))
        handler.http_get_download.assert_not_called()


class TestPatch(unittest.TestCase):
    def test_a_top_level_set_needs_no_read(self):
        api = FakeApi()
        handler = _handler(api)
        handler.get = MagicMock()
        code, out = _run(handler.cmd_patch, pk="42", field_exprs=["category=farming"])
        self.assertEqual(code, EXIT_OK)
        handler.get.assert_not_called()
        self.assertEqual(api.sent, [("PATCH", 42, {"category": {"id": "farming"}})])
        self.assertIn("resource 42: The resource was updated successfully", out)

    def test_a_nested_set_sends_the_whole_top_level_value(self):
        api = FakeApi()
        code, _ = _run(
            _handler(api).cmd_patch,
            pk="42",
            field_exprs=["tkeywords.AGROVOC=http://x/c_1"],
        )
        self.assertEqual(code, EXIT_OK)
        sent = api.sent[0][2]["tkeywords"]
        self.assertEqual(sent["AGROVOC"], [{"id": "http://x/c_1"}])
        self.assertEqual(sent["GEMET"], INSTANCE["tkeywords"]["GEMET"])

    def test_set_and_field_combine(self):
        api = FakeApi()
        _run(
            _handler(api).cmd_patch,
            pk="42",
            fields='{"title": "t", "edition": "1"}',
            field_exprs=["title=from field"],
        )
        self.assertEqual(api.sent[0][2], {"title": "from field", "edition": "1"})

    def test_nothing_to_change(self):
        with self.assertLogs(level="ERROR"):
            code, _ = _run(_handler(FakeApi()).cmd_patch, pk="42")
        self.assertEqual(code, EXIT_USAGE)

    def test_dry_run_sends_nothing(self):
        api = FakeApi()
        code, out = _run(
            _handler(api).cmd_patch,
            pk="42",
            field_exprs=["hkeywords+=water"],
            dry_run=True,
        )
        self.assertEqual(code, EXIT_OK)
        self.assertEqual(api.sent, [])
        self.assertEqual(
            json.loads(out), {"42": {"hkeywords": ["soil", "crop modeling", "water"]}}
        )

    def test_linkedresources_is_refused(self):
        cases: List[Dict[str, Any]] = [
            {"field_exprs": ["linkedresources+=2087"]},
            {"fields": '{"linkedresources": []}'},
        ]
        for kwargs in cases:
            with self.subTest(**kwargs):
                api = FakeApi()
                with self.assertLogs(level="ERROR") as logs:
                    code, _ = _run(_handler(api).cmd_patch, pk="42", **kwargs)
                self.assertEqual(code, EXIT_USAGE)
                self.assertEqual(api.sent, [])
                self.assertIn("linked-resources", "\n".join(logs.output))

    def test_a_rejected_payload_sends_nothing_for_any_pk(self):
        api = FakeApi(instances={1: INSTANCE, 2: INSTANCE})
        with self.assertLogs(level="ERROR"):
            code, out = _run(
                _handler(api).cmd_patch, pk="1-2", fields='{"date": "not-a-date"}'
            )
        self.assertEqual(code, EXIT_USAGE)
        self.assertEqual(api.sent, [])
        self.assertIn("$.date", out)

    def test_no_validate_leaves_it_to_the_server(self):
        api = FakeApi(
            writes={
                42: (
                    422,
                    {
                        "message": "Some errors were found",
                        "extraErrors": {"date": {"__errors": ["invalid format"]}},
                    },
                )
            }
        )
        code, out = _run(
            _handler(api).cmd_patch,
            pk="42",
            fields='{"date": "not-a-date"}',
            no_validate=True,
        )
        self.assertEqual(code, EXIT_FAILED)
        self.assertEqual(len(api.sent), 1)
        self.assertIn("resource 42: Some errors were found", out)
        self.assertIn("invalid format", out)

    def test_a_bulk_patch_goes_on_past_a_failing_pk(self):
        api = FakeApi(instances={1: INSTANCE, 2: INSTANCE, 3: INSTANCE})
        handler = _handler(api)
        original = handler.http_send.side_effect

        def failing_on_2(method, endpoint, **kwargs):
            if method == "PATCH" and endpoint.endswith("/2"):
                return None
            return original(method, endpoint, **kwargs)

        handler.http_send.side_effect = failing_on_2
        with self.assertLogs(level="ERROR"):
            code, _ = _run(handler.cmd_patch, pk="1-3", field_exprs=["edition=2"])
        self.assertEqual(code, EXIT_FAILED)
        self.assertEqual([pk for _, pk, _ in api.sent], [1, 3])

    def test_json_output(self):
        code, out = _run(
            _handler(FakeApi()).cmd_patch,
            pk="42",
            field_exprs=["edition=2"],
            json=True,
        )
        self.assertEqual(code, EXIT_OK)
        record = json.loads(out)[0]
        self.assertEqual((record["pk"], record["status"]), (42, 200))


class TestPut(unittest.TestCase):
    def test_a_round_trip_leaves_links_and_read_only_fields_out(self):
        api = FakeApi()
        with self.assertLogs(level="INFO") as logs:
            code, _ = _run(_handler(api).cmd_put, pk="42", fields=json.dumps(INSTANCE))
        self.assertEqual(code, EXIT_OK)
        method, pk, payload = api.sent[0]
        self.assertEqual((method, pk), ("PATCH", 42), "never an http PUT")
        self.assertNotIn("linkedresources", payload)
        self.assertNotIn("uuid", payload)
        self.assertEqual(payload["date_type"], "Creation", "sent as given")
        self.assertIn("linked-resources", "\n".join(logs.output))

    def test_required_fields_are_checked(self):
        api = FakeApi()
        instance = dict(INSTANCE, category=None)
        with self.assertLogs(level="ERROR"):
            code, out = _run(
                _handler(api).cmd_put, pk="42", fields=json.dumps(instance)
            )
        self.assertEqual(code, EXIT_USAGE)
        self.assertEqual(api.sent, [])
        self.assertIn("$.category", out)

    def test_unknown_keys_are_refused(self):
        api = FakeApi()
        with self.assertLogs(level="ERROR"):
            code, _ = _run(
                _handler(api).cmd_put,
                pk="42",
                fields=json.dumps(dict(INSTANCE, titel="x")),
            )
        self.assertEqual(code, EXIT_USAGE)
        self.assertEqual(api.sent, [])


class TestValidate(unittest.TestCase):
    def test_valid_and_invalid(self):
        api = FakeApi(instances={1: INSTANCE, 2: dict(INSTANCE, category=None)})
        code, out = _run(_handler(api).cmd_validate, pk="1,2")
        self.assertEqual(code, EXIT_FAILED)
        self.assertIn("resource 1: valid", out)
        self.assertIn("resource 2: invalid, 1 violation(s)", out)

    def test_all_valid(self):
        code, _ = _run(_handler(FakeApi()).cmd_validate, pk="42")
        self.assertEqual(code, EXIT_OK)

    def test_a_missing_resource_fails(self):
        with self.assertLogs(level="ERROR"):
            code, _ = _run(_handler(FakeApi()).cmd_validate, pk="999")
        self.assertEqual(code, EXIT_FAILED)


if __name__ == "__main__":
    unittest.main()
