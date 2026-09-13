"""uuid-as-identifier support, issue #160."""

import unittest
from unittest.mock import patch

from geonoderest.attributes import GeonodeAttributeHandler
from geonoderest.datasets import GeonodeDatasetsHandler
from geonoderest.exceptions import (
    InvalidPkError,
    ResourceNotFoundError,
    UuidTypeMismatchError,
)
from geonoderest.exitcodes import EXIT_FAILED, EXIT_OK, EXIT_USAGE
from geonoderest.geoapps import GeonodeGeoappsHandler
from geonoderest.groups import GeonodeGroupsHandler
from geonoderest.identifier import (
    ANY_RESOURCE_TYPE,
    canonical_uuid,
    is_uuid,
    resource_type_matches,
)
from geonoderest.linkedresources import GeonodeLinkedResourcesHandler
from geonoderest.maps import GeonodeMapsHandler
from geonoderest.resources import GeonodeResourceHandler
from geonoderest.users import GeonodeUsersHandler

UUID = "550e8400-e29b-41d4-a716-446655440000"
OTHER_UUID = "6ba7b810-9dad-11d1-80b4-00c04fd430c8"


def _api(resource_type="dataset", pk="42", rows=None):
    """Stand in for http_get: the uuid filter query, then the detail fetch."""

    def _get(endpoint, params=None, **kwargs):
        if endpoint == "resources/":
            if rows is not None:
                return {"resources": rows}
            return {"resources": [{"pk": pk, "resource_type": resource_type}]}
        # the detail call: hand back whichever singular key the handler unwraps
        obj = {"pk": int(pk), "title": "T"}
        return {k: obj for k in ("dataset", "document", "map", "geoapp", "resource")}

    return _get


class TestIsUuid(unittest.TestCase):
    def test_accepts_a_canonical_uuid(self):
        self.assertTrue(is_uuid(UUID))
        self.assertTrue(is_uuid(OTHER_UUID))

    def test_accepts_uppercase(self):
        self.assertTrue(is_uuid(UUID.upper()))

    def test_rejects_pks_ranges_and_lists(self):
        for value in ("42", "1-5", "1,2,3", "0", ""):
            self.assertFalse(is_uuid(value), value)

    def test_rejects_near_misses(self):
        """strictness matters: this is the pk-vs-uuid switch"""
        for value in (
            "550e8400-e29b-41d4-a716-44665544000",  # a digit short
            "550e8400-e29b-41d4-a716-4466554400zz",  # not hex
            "550e8400e29b41d4a716",  # too short, no dashes
        ):
            self.assertFalse(is_uuid(value), value)

    def test_rejects_non_strings(self):
        for value in (42, None, ["a"]):
            self.assertFalse(is_uuid(value), value)


class TestResourceTypeMatches(unittest.TestCase):
    def test_core_types_match_by_name(self):
        for t in ("dataset", "document", "map"):
            self.assertTrue(resource_type_matches(t, t))

    def test_core_types_do_not_match_each_other(self):
        self.assertFalse(resource_type_matches("map", "dataset"))
        self.assertFalse(resource_type_matches("document", "map"))

    def test_any_matches_everything(self):
        for t in ("dataset", "map", "geostory", "something-new"):
            self.assertTrue(resource_type_matches(t, ANY_RESOURCE_TYPE))

    def test_geoapp_matches_by_exclusion(self):
        """GeoNode reports a geoapp's subtype, never the word 'geoapp'"""
        for t in ("geostory", "dashboard", "a-deployments-custom-app"):
            self.assertTrue(resource_type_matches(t, "geoapp"), t)

    def test_geoapp_does_not_match_a_core_type(self):
        for t in ("dataset", "document", "map"):
            self.assertFalse(resource_type_matches(t, "geoapp"), t)


class TestResolveIdentifier(unittest.TestCase):
    @patch.object(GeonodeDatasetsHandler, "http_get")
    def test_a_pk_is_returned_untouched_and_costs_no_request(self, mock_get):
        handler = GeonodeDatasetsHandler(env={})
        self.assertEqual(handler.__resolve_identifier__("42"), 42)
        self.assertEqual(handler.__resolve_identifier__(42), 42)
        mock_get.assert_not_called()

    @patch.object(GeonodeDatasetsHandler, "http_get")
    def test_a_uuid_resolves_to_its_pk(self, mock_get):
        mock_get.side_effect = _api(pk="7")
        self.assertEqual(GeonodeDatasetsHandler(env={}).__resolve_identifier__(UUID), 7)

    @patch.object(GeonodeDatasetsHandler, "http_get")
    def test_the_lookup_carries_the_filter_and_advertised_all(self, mock_get):
        """advertised=all, or a non-advertised resource is invisible to uuid
        lookup while GET resources/<pk> still returns it"""
        mock_get.side_effect = _api()
        GeonodeDatasetsHandler(env={}).__resolve_identifier__(UUID)
        kwargs = mock_get.call_args.kwargs
        self.assertEqual(kwargs["endpoint"], "resources/")
        self.assertEqual(kwargs["params"]["filter{uuid}"], UUID)
        self.assertEqual(kwargs["params"]["advertised"], "all")

    @patch.object(GeonodeDatasetsHandler, "http_get")
    def test_a_wrong_type_raises(self, mock_get):
        mock_get.side_effect = _api(resource_type="map")
        with self.assertRaises(UuidTypeMismatchError) as cm:
            GeonodeDatasetsHandler(env={}).__resolve_identifier__(UUID)
        self.assertIn("is a map", str(cm.exception))

    @patch.object(GeonodeDatasetsHandler, "http_get")
    def test_an_unknown_uuid_raises_not_found(self, mock_get):
        mock_get.side_effect = _api(rows=[])
        with self.assertRaises(ResourceNotFoundError):
            GeonodeDatasetsHandler(env={}).__resolve_identifier__(UUID)

    @patch.object(GeonodeDatasetsHandler, "http_get", return_value=None)
    def test_a_failed_lookup_is_not_silently_a_pk(self, _):
        from geonoderest.exceptions import GeoNodeRestException

        with self.assertRaises(GeoNodeRestException):
            GeonodeDatasetsHandler(env={}).__resolve_identifier__(UUID)

    @patch.object(GeonodeDatasetsHandler, "http_get")
    def test_a_string_pk_from_the_api_is_returned_as_an_int(self, mock_get):
        """the API serializes pk as a string"""
        mock_get.side_effect = _api(pk="1234")
        pk = GeonodeDatasetsHandler(env={}).__resolve_identifier__(UUID)
        self.assertIsInstance(pk, int)
        self.assertEqual(pk, 1234)

    def test_garbage_raises_invalid_pk(self):
        with self.assertRaises(InvalidPkError):
            GeonodeDatasetsHandler(env={}).__resolve_identifier__("not-an-id")

    @patch.object(GeonodeUsersHandler, "http_get")
    def test_users_have_no_uuid(self, mock_get):
        with self.assertRaises(InvalidPkError) as cm:
            GeonodeUsersHandler(env={}).__resolve_identifier__(UUID)
        self.assertIn("identified by pk", str(cm.exception))
        mock_get.assert_not_called()

    @patch.object(GeonodeGroupsHandler, "http_get")
    def test_groups_have_no_uuid(self, mock_get):
        with self.assertRaises(InvalidPkError):
            GeonodeGroupsHandler(env={}).__resolve_identifier__(UUID)
        mock_get.assert_not_called()

    @patch.object(GeonodeMapsHandler, "http_get")
    def test_expected_overrides_the_handlers_own_type(self, mock_get):
        """maps maplayers add takes *dataset* identifiers"""
        mock_get.side_effect = _api(resource_type="dataset", pk="9")
        handler = GeonodeMapsHandler(env={})
        self.assertEqual(
            handler.__resolve_identifier__(UUID, expected="dataset"),
            9,
        )
        with self.assertRaises(UuidTypeMismatchError):
            handler.__resolve_identifier__(UUID)  # defaults to "map"


class TestHandlerResourceTypes(unittest.TestCase):
    def test_each_handler_declares_the_right_type(self):
        self.assertEqual(GeonodeDatasetsHandler.UUID_RESOURCE_TYPE, "dataset")
        self.assertEqual(GeonodeMapsHandler.UUID_RESOURCE_TYPE, "map")
        self.assertEqual(GeonodeGeoappsHandler.UUID_RESOURCE_TYPE, "geoapp")
        self.assertEqual(GeonodeAttributeHandler.UUID_RESOURCE_TYPE, "dataset")
        self.assertEqual(GeonodeResourceHandler.UUID_RESOURCE_TYPE, ANY_RESOURCE_TYPE)
        self.assertEqual(
            GeonodeLinkedResourcesHandler.UUID_RESOURCE_TYPE, ANY_RESOURCE_TYPE
        )

    def test_non_resource_handlers_have_none(self):
        self.assertIsNone(GeonodeUsersHandler.UUID_RESOURCE_TYPE)
        self.assertIsNone(GeonodeGroupsHandler.UUID_RESOURCE_TYPE)


class TestParsePkStringWithUuids(unittest.TestCase):
    @patch.object(GeonodeDatasetsHandler, "http_get")
    def test_a_lone_uuid_resolves(self, mock_get):
        mock_get.side_effect = _api(pk="7")
        self.assertEqual(GeonodeDatasetsHandler(env={}).__parse_pk_string__(UUID), [7])

    def test_pk_forms_still_work(self):
        handler = GeonodeDatasetsHandler(env={})
        self.assertEqual(handler.__parse_pk_string__("42"), [42])
        self.assertEqual(handler.__parse_pk_string__("1-3"), [1, 2, 3])
        self.assertEqual(handler.__parse_pk_string__("1,2,3"), [1, 2, 3])

    def test_a_uuid_list_is_refused_with_a_useful_message(self):
        """a uuid list has both commas and dashes; 'not a range' explained nothing"""
        with self.assertRaises(InvalidPkError) as cm:
            GeonodeDatasetsHandler(env={}).__parse_pk_string__(f"{UUID},{OTHER_UUID}")
        self.assertIn("on its own", str(cm.exception))

    def test_a_uuid_range_is_refused_with_a_useful_message(self):
        with self.assertRaises(InvalidPkError) as cm:
            GeonodeDatasetsHandler(env={}).__parse_pk_string__(f"{UUID}-{OTHER_UUID}")
        self.assertIn("on its own", str(cm.exception))


class TestCommandsAcceptUuids(unittest.TestCase):
    @patch.object(GeonodeDatasetsHandler, "http_get")
    def test_describe_by_uuid_fetches_the_resolved_pk(self, mock_get):
        mock_get.side_effect = _api(pk="7")
        with patch("geonoderest.geonodeobject.print_json"):
            code = GeonodeDatasetsHandler(env={}).cmd_describe(pk=UUID, json=False)
        self.assertEqual(code, EXIT_OK)
        endpoints = [c.kwargs.get("endpoint") for c in mock_get.call_args_list]
        self.assertEqual(endpoints, ["resources/", "datasets/7"])

    @patch.object(GeonodeDatasetsHandler, "http_get")
    def test_describe_by_pk_makes_no_resolution_request(self, mock_get):
        mock_get.side_effect = _api()
        with patch("geonoderest.geonodeobject.print_json"):
            GeonodeDatasetsHandler(env={}).cmd_describe(pk="7", json=False)
        endpoints = [c.kwargs.get("endpoint") for c in mock_get.call_args_list]
        self.assertEqual(endpoints, ["datasets/7"])

    @patch.object(GeonodeDatasetsHandler, "http_get")
    def test_wrong_type_exits_usage(self, mock_get):
        mock_get.side_effect = _api(resource_type="map")
        with self.assertLogs(level="ERROR"):
            code = GeonodeDatasetsHandler(env={}).cmd_describe(pk=UUID, json=False)
        self.assertEqual(code, EXIT_USAGE)

    @patch.object(GeonodeUsersHandler, "http_get")
    def test_a_uuid_on_a_users_verb_exits_usage(self, mock_get):
        with self.assertLogs(level="ERROR"):
            code = GeonodeUsersHandler(env={}).cmd_delete(pk=UUID)
        self.assertEqual(code, EXIT_USAGE)
        mock_get.assert_not_called()

    @patch.object(GeonodeGeoappsHandler, "http_get")
    def test_a_geostory_uuid_satisfies_the_geoapps_verb(self, mock_get):
        mock_get.side_effect = _api(resource_type="geostory", pk="5")
        with patch("geonoderest.geonodeobject.print_json"):
            code = GeonodeGeoappsHandler(env={}).cmd_describe(pk=UUID, json=False)
        self.assertEqual(code, EXIT_OK)
        self.assertEqual(mock_get.call_args_list[-1].kwargs["endpoint"], "geoapps/5")

    @patch.object(GeonodeMapsHandler, "add_maplayers", return_value={"ok": 1})
    @patch.object(GeonodeMapsHandler, "http_get")
    def test_maplayers_add_resolves_map_and_datasets_separately(
        self, mock_get, mock_add
    ):
        def api(endpoint, params=None, **kwargs):
            if endpoint == "resources/":
                given = params["filter{uuid}"]
                if given == UUID:
                    return {"resources": [{"pk": "7", "resource_type": "map"}]}
                return {"resources": [{"pk": "9", "resource_type": "dataset"}]}
            return {"map": {"pk": 7}}

        mock_get.side_effect = api
        with patch("geonoderest.maps.print_json"):
            GeonodeMapsHandler(env={}).cmd_maplayers_add(
                pk=UUID, datasets=[OTHER_UUID], json=False
            )
        self.assertEqual(mock_add.call_args.kwargs["pk"], 7)
        self.assertEqual(mock_add.call_args.kwargs["datasets"], [9])

    @patch.object(GeonodeLinkedResourcesHandler, "http_post")
    @patch.object(GeonodeLinkedResourcesHandler, "http_get")
    def test_linked_resources_empty_list_still_costs_no_lookup(
        self, mock_get, mock_post
    ):
        """the #151 empty-list guard must run before any resolution"""
        with self.assertLogs(level="ERROR"):
            code = GeonodeLinkedResourcesHandler(env={}).cmd_add(pk=UUID, linked_to=[])
        self.assertEqual(code, EXIT_USAGE)
        mock_get.assert_not_called()
        mock_post.assert_not_called()


class TestReviewFindings(unittest.TestCase):
    """regressions found reviewing this change - one case per finding"""

    def test_non_canonical_spellings_normalise(self):
        """filter{uuid} is an exact match, so what we send must be canonical"""
        for form in (
            UUID.upper(),
            "{" + UUID + "}",
            "urn:uuid:" + UUID,
            UUID.replace("-", ""),
        ):
            self.assertEqual(canonical_uuid(form), UUID, form)

    @patch.object(GeonodeDatasetsHandler, "http_get")
    def test_an_uppercase_uuid_is_sent_lowercase(self, mock_get):
        """a uuid pasted from a catalogue export used to match nothing"""
        mock_get.side_effect = _api(pk="42")
        GeonodeDatasetsHandler(env={}).__resolve_identifier__(UUID.upper())
        self.assertEqual(mock_get.call_args.kwargs["params"]["filter{uuid}"], UUID)

    @patch.object(GeonodeDatasetsHandler, "http_get")
    def test_a_row_for_a_different_uuid_is_refused(self, mock_get):
        """if the filter were ever dropped, row[0] must not be acted on"""
        mock_get.return_value = {
            "resources": [{"pk": "999", "uuid": OTHER_UUID, "resource_type": "dataset"}]
        }
        with self.assertRaises(ResourceNotFoundError) as cm:
            GeonodeDatasetsHandler(env={}).__resolve_identifier__(UUID)
        self.assertIn("ignored the uuid filter", str(cm.exception))

    @patch.object(GeonodeDatasetsHandler, "http_get")
    def test_a_malformed_returned_uuid_is_refused_not_raised(self, mock_get):
        mock_get.return_value = {
            "resources": [
                {"pk": "999", "uuid": "not-a-uuid", "resource_type": "dataset"}
            ]
        }
        with self.assertRaises(ResourceNotFoundError):
            GeonodeDatasetsHandler(env={}).__resolve_identifier__(UUID)

    @patch.object(GeonodeDatasetsHandler, "http_get")
    def test_a_row_without_a_uuid_field_still_resolves(self, mock_get):
        """a slim response must not be rejected by the mismatch guard"""
        mock_get.return_value = {
            "resources": [{"pk": "42", "resource_type": "dataset"}]
        }
        self.assertEqual(
            GeonodeDatasetsHandler(env={}).__resolve_identifier__(UUID), 42
        )

    @patch.object(GeonodeResourceHandler, "http_get_download")
    @patch.object(GeonodeResourceHandler, "http_get")
    def test_resources_metadata_resolves_a_uuid(self, mock_get, mock_dl):
        """the pk arg became type=str but cmd_metadata was not resolving it"""

        def api(endpoint, params=None, **kwargs):
            if endpoint == "resources/":
                return {
                    "resources": [
                        {"pk": "42", "uuid": UUID, "resource_type": "dataset"}
                    ]
                }
            return {"resource": {"links": [{"name": "ISO", "url": "http://x/iso.xml"}]}}

        mock_get.side_effect = api
        mock_dl.return_value.text = "<xml/>"
        code = GeonodeResourceHandler(env={}).cmd_metadata(pk=UUID, json=False)
        self.assertEqual(code, EXIT_OK)
        endpoints = [c.kwargs.get("endpoint") for c in mock_get.call_args_list]
        self.assertEqual(endpoints, ["resources/", "resources/42"])

    @patch.object(GeonodeResourceHandler, "http_get", return_value=None)
    def test_resources_metadata_failure_is_an_exit_code(self, _):
        """metadata() used to do None["resource"]"""
        with self.assertLogs(level="ERROR"):
            code = GeonodeResourceHandler(env={}).cmd_metadata(pk="42", json=False)
        self.assertEqual(code, EXIT_FAILED)

    @patch.object(GeonodeMapsHandler, "http_get")
    def test_maplayers_empty_list_costs_no_lookup(self, mock_get):
        """the #151 empty-list guard must run before resolution, as it does for
        linked-resources"""
        handler = GeonodeMapsHandler(env={})
        for verb in ("cmd_maplayers_add", "cmd_maplayers_remove"):
            with self.subTest(verb=verb), self.assertLogs(level="ERROR"):
                code = getattr(handler, verb)(pk=UUID, datasets=[], json=False)
            self.assertEqual(code, EXIT_USAGE)
        mock_get.assert_not_called()


class TestSecondReviewFindings(unittest.TestCase):
    """second review pass - validate before resolving, and no tracebacks"""

    @patch.object(GeonodeAttributeHandler, "http_get")
    def test_attributes_patch_validates_before_resolving(self, mock_get):
        """a missing --set must say so, not report a failed uuid lookup"""
        with self.assertLogs(level="ERROR") as logs:
            code = GeonodeAttributeHandler(env={}).cmd_patch(pk=UUID, json=False)
        self.assertEqual(code, EXIT_USAGE)
        self.assertIn("must be provided", "".join(logs.output))
        mock_get.assert_not_called()

    def test_an_unknown_resource_type_never_satisfies_geoapp(self):
        """geoapp is an exclusion test, so "" would otherwise pass it"""
        for actual in ("", None):
            self.assertFalse(resource_type_matches(actual or "", "geoapp"), actual)
            self.assertFalse(resource_type_matches(actual or "", "dataset"), actual)

    @patch.object(GeonodeGeoappsHandler, "http_get")
    def test_a_row_without_a_resource_type_is_refused(self, mock_get):
        mock_get.return_value = {"resources": [{"pk": "42", "uuid": UUID}]}
        with self.assertRaises(UuidTypeMismatchError):
            GeonodeGeoappsHandler(env={}).__resolve_identifier__(UUID)

    @patch.object(GeonodeResourceHandler, "http_get")
    def test_metadata_survives_an_unexpected_payload(self, mock_get):
        """response["resource"] used to raise KeyError"""
        mock_get.return_value = {"unexpected": {}}
        with self.assertLogs(level="ERROR"):
            code = GeonodeResourceHandler(env={}).cmd_metadata(pk="42", json=False)
        self.assertEqual(code, EXIT_FAILED)

    @patch.object(GeonodeResourceHandler, "http_get")
    def test_metadata_reports_a_missing_link_type(self, mock_get):
        """the link lookup used to raise IndexError"""
        mock_get.return_value = {
            "resource": {"links": [{"name": "Atom", "url": "http://x/a"}]}
        }
        with self.assertLogs(level="ERROR") as logs:
            code = GeonodeResourceHandler(env={}).cmd_metadata(
                pk="42", metadata_type="ISO", json=False
            )
        self.assertEqual(code, EXIT_FAILED)
        # says which types the resource does have
        self.assertIn("Atom", "".join(logs.output))

    @patch.object(GeonodeMapsHandler, "http_get")
    def test_widget_flags_are_validated_before_identifiers(self, mock_get):
        """--maplayer on a textbox must name the wrong flag, not a type mismatch"""
        with self.assertLogs(level="ERROR") as logs:
            GeonodeMapsHandler(env={}).cmd_widgets_add(
                pk=7, widget_type="textbox", maplayer=UUID, title="t", json=False
            )
        self.assertIn("--maplayer cannot be used", "".join(logs.output))
        mock_get.assert_not_called()

    @patch.object(GeonodeMapsHandler, "http_get")
    def test_an_unknown_widget_type_is_reported_before_resolving(self, mock_get):
        with self.assertLogs(level="ERROR") as logs:
            GeonodeMapsHandler(env={}).cmd_widgets_add(
                pk=UUID, widget_type="nonsense", json=False
            )
        self.assertIn("unknown widget type", "".join(logs.output))
        mock_get.assert_not_called()


class TestHelpMentionsUuid(unittest.TestCase):
    """--help is the only place a user discovers the feature"""

    def _help(self, *argv):
        import contextlib
        import io as _io

        from geonoderest.geonodectl import geonodectl

        out = _io.StringIO()
        with patch("sys.argv", ["geonodectl", *argv, "--help"]):
            with contextlib.redirect_stdout(out), self.assertRaises(SystemExit):
                geonodectl()
        return out.getvalue()

    def test_resource_verbs_advertise_uuid(self):
        for argv in (
            ("dataset", "describe"),
            ("maps", "get-blob"),
            ("attributes", "describe"),
            ("resources", "metadata"),
        ):
            with self.subTest(argv=argv):
                self.assertIn("uuid", self._help(*argv))

    def test_user_and_group_verbs_do_not(self):
        for argv in (("users", "describe"), ("groups", "patch")):
            with self.subTest(argv=argv):
                self.assertNotIn("uuid", self._help(*argv))


if __name__ == "__main__":
    unittest.main()
