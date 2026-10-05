import unittest
from copy import deepcopy

from geonoderest.exceptions import GeonodeUsageError, MetadataFieldError
from geonoderest.metadatafields import (
    APPEND,
    JSON,
    REMOVE,
    SET,
    apply_ops,
    check_payload_keys,
    coerce,
    flatten_errors,
    for_validation,
    lookup_paths,
    lookup_url,
    needs_current_instance,
    parse_field_expr,
    payload_schema,
    resolve_property,
)
from geonoderest.validate import build_validator, collect_errors
from metadata_schema import INSTANCE, SCHEMA

SCHEMA_URL = "http://example.org/api/v2/metadata/schema"


def _apply(*exprs, payload=None, current=INSTANCE):
    ops = [parse_field_expr(expr) for expr in exprs]
    return apply_ops(SCHEMA, ops, payload, current)


class TestParseFieldExpr(unittest.TestCase):
    def test_operators(self):
        cases = {
            "title=x": (("title",), SET, "x"),
            "count:=3": (("count",), JSON, "3"),
            "hkeywords+=soil": (("hkeywords",), APPEND, "soil"),
            "hkeywords-=soil": (("hkeywords",), REMOVE, "soil"),
            "tkeywords.AGROVOC=c_1": (("tkeywords", "AGROVOC"), SET, "c_1"),
        }
        for expr, (path, op, raw) in cases.items():
            with self.subTest(expr=expr):
                parsed = parse_field_expr(expr)
                self.assertEqual((parsed.path, parsed.op, parsed.raw), (path, op, raw))

    def test_value_may_contain_equals_signs(self):
        self.assertEqual(parse_field_expr("title=a=b").raw, "a=b")
        self.assertEqual(parse_field_expr('count:={"a": "b=c"}').raw, '{"a": "b=c"}')

    def test_empty_value_is_allowed(self):
        self.assertEqual(parse_field_expr("edition=").raw, "")

    def test_malformed(self):
        for expr in ("title", "=x", "a..b=x", ".a=x", "contacts.[].users=1"):
            with self.subTest(expr=expr), self.assertRaises(MetadataFieldError):
                parse_field_expr(expr)

    def test_is_a_usage_error(self):
        """so the cmdline turns it into EXIT_USAGE"""
        with self.assertRaises(GeonodeUsageError):
            parse_field_expr("title")


class TestResolveProperty(unittest.TestCase):
    def test_top_level_and_nested(self):
        self.assertEqual(resolve_property(SCHEMA, "title")["type"], "string")
        self.assertIn("ui:options", resolve_property(SCHEMA, "tkeywords.AGROVOC"))
        self.assertIn(
            "ui:options", resolve_property(SCHEMA, "contacts.contact_roles.[].users")
        )

    def test_unknown_field_suggests_a_close_match(self):
        with self.assertRaises(MetadataFieldError) as cm:
            resolve_property(SCHEMA, "titel")
        self.assertIn("did you mean title", str(cm.exception))

    def test_unknown_nested_field_lists_its_siblings(self):
        with self.assertRaises(MetadataFieldError) as cm:
            resolve_property(SCHEMA, "tkeywords.AGRO")
        self.assertIn("AGROVOC", str(cm.exception))

    def test_array_step_on_a_non_array(self):
        with self.assertRaises(MetadataFieldError):
            resolve_property(SCHEMA, "title.[]")


class TestLookups(unittest.TestCase):
    def test_url_in_both_forms(self):
        self.assertEqual(
            lookup_url(SCHEMA["properties"]["category"]),
            "/api/v2/metadata/autocomplete/categories",
        )
        self.assertEqual(
            lookup_url(SCHEMA["properties"]["hkeywords"]),
            "/api/v2/metadata/autocomplete/hkeywords",
        )
        self.assertIsNone(lookup_url(SCHEMA["properties"]["title"]))

    def test_thesaurus_url_comes_from_the_schema(self):
        """the url names the thesaurus by id, so it cannot be built from AGROVOC"""
        self.assertEqual(
            lookup_url(resolve_property(SCHEMA, "tkeywords.AGROVOC")),
            "/api/v2/metadata/autocomplete/thesaurus/2/keywords",
        )

    def test_every_path_with_a_lookup(self):
        self.assertEqual(
            lookup_paths(SCHEMA),
            [
                "category",
                "regions",
                "hkeywords",
                "tkeywords.AGROVOC",
                "tkeywords.GEMET",
                "contacts.owner",
                "contacts.contact_roles.[].users",
                "linkedresources",
            ],
        )


class TestCoerce(unittest.TestCase):
    def _coerce(self, field, raw):
        return coerce(resolve_property(SCHEMA, field), raw, field)

    def test_string_as_is(self):
        self.assertEqual(self._coerce("title", "a, b"), "a, b")

    def test_empty_is_null_only_where_null_is_allowed(self):
        self.assertIsNone(self._coerce("edition", ""))
        self.assertEqual(self._coerce("title", ""), "")

    def test_enum_by_const_or_title(self):
        self.assertEqual(self._coerce("language", "eng"), "eng")
        self.assertEqual(self._coerce("language", "English"), "eng")
        self.assertEqual(self._coerce("language", "GERMAN"), "ger")
        self.assertEqual(self._coerce("date_type", "Publication"), "publication")

    def test_unknown_enum_value_lists_the_choices(self):
        with self.assertRaises(MetadataFieldError) as cm:
            self._coerce("language", "Klingon")
        self.assertIn("eng (English)", str(cm.exception))

    def test_reference(self):
        self.assertEqual(self._coerce("category", "biota"), {"id": "biota"})

    def test_arrays(self):
        self.assertEqual(
            self._coerce("regions", "96, 97"), [{"id": "96"}, {"id": "97"}]
        )
        self.assertEqual(self._coerce("hkeywords", "a,b,"), ["a", "b"])

    def test_number_and_boolean(self):
        self.assertEqual(self._coerce("count", "3"), 3)
        self.assertIs(self._coerce("reviewed", "TRUE"), True)
        for field, raw in (("count", "three"), ("reviewed", "yes")):
            with self.subTest(field=field), self.assertRaises(MetadataFieldError):
                self._coerce(field, raw)

    def test_complex_fields_need_json(self):
        with self.assertRaises(MetadataFieldError) as cm:
            self._coerce("contacts.contact_roles", "x")
        self.assertIn("contacts.contact_roles:=<json>", str(cm.exception))


class TestApplyOps(unittest.TestCase):
    def test_top_level_set_needs_no_current_instance(self):
        ops = [parse_field_expr("license=CC-BY")]
        self.assertFalse(needs_current_instance(ops))
        self.assertEqual(
            _apply("category=farming", current=None), {"category": {"id": "farming"}}
        )

    def test_nested_and_array_edits_need_it(self):
        for expr in ("tkeywords.AGROVOC=x", "hkeywords+=x", "hkeywords-=x"):
            with self.subTest(expr=expr):
                self.assertTrue(needs_current_instance([parse_field_expr(expr)]))

    def test_nested_set_keeps_the_sibling_keys(self):
        """PATCH replaces top-level values wholesale - GEMET must survive"""
        payload = _apply("tkeywords.AGROVOC=http://x/c_1")
        self.assertEqual(payload["tkeywords"]["AGROVOC"], [{"id": "http://x/c_1"}])
        self.assertEqual(payload["tkeywords"]["GEMET"], INSTANCE["tkeywords"]["GEMET"])

    def test_append_skips_what_is_there(self):
        self.assertEqual(
            _apply("hkeywords+=soil,water")["hkeywords"],
            ["soil", "crop modeling", "water"],
        )
        self.assertEqual(
            _apply("regions+=96,97")["regions"],
            [{"id": "96", "label": "Germany"}, {"id": "97"}],
        )

    def test_remove_matches_references_by_id(self):
        self.assertEqual(_apply("regions-=96")["regions"], [])
        self.assertEqual(_apply("hkeywords-=soil")["hkeywords"], ["crop modeling"])

    def test_removing_what_is_not_there_is_a_warning(self):
        with self.assertLogs(level="WARNING"):
            payload = _apply("hkeywords-=water")
        self.assertEqual(payload["hkeywords"], INSTANCE["hkeywords"])

    def test_append_on_a_non_array(self):
        with self.assertRaises(MetadataFieldError):
            _apply("title+=x")

    def test_raw_json(self):
        self.assertEqual(_apply("count:=3", current=None), {"count": 3})
        with self.assertRaises(MetadataFieldError):
            _apply("count:={not json", current=None)

    def test_fields_apply_on_top_of_a_payload(self):
        base = {"title": "from --set", "edition": "1"}
        payload = _apply("title=from --field", payload=base, current=None)
        self.assertEqual(payload, {"title": "from --field", "edition": "1"})
        self.assertEqual(base["title"], "from --set", "the base must not change")

    def test_the_current_instance_is_not_modified(self):
        current = deepcopy(INSTANCE)
        apply_ops(SCHEMA, [parse_field_expr("hkeywords+=water")], None, current)
        self.assertEqual(current, INSTANCE)


class TestPayloadChecks(unittest.TestCase):
    def test_unknown_and_read_only_keys(self):
        with self.assertRaises(MetadataFieldError):
            check_payload_keys(SCHEMA, {"titel": "x"})
        with self.assertRaises(MetadataFieldError) as cm:
            check_payload_keys(SCHEMA, {"uuid": "x"})
        self.assertIn("read-only", str(cm.exception))
        check_payload_keys(SCHEMA, {"title": "x"})

    def _errors(self, payload):
        validator = build_validator(payload_schema(SCHEMA, payload), SCHEMA_URL)
        return collect_errors(validator, for_validation(SCHEMA, payload))

    def test_a_partial_payload_ignores_required(self):
        """a PATCH carries some fields only"""
        self.assertEqual(self._errors({"edition": "2"}), [])

    def test_each_value_is_checked_against_its_property(self):
        errors = self._errors({"date": "not-a-date", "count": "3"})
        self.assertEqual(sorted(e["path"] for e in errors), ["$.count", "$.date"])


class TestForValidation(unittest.TestCase):
    def _errors(self, instance):
        validator = build_validator(SCHEMA, SCHEMA_URL)
        return collect_errors(validator, for_validation(SCHEMA, instance))

    def test_an_instance_as_geonode_hands_it_out_is_valid(self):
        self.assertEqual(self._errors(INSTANCE), [])

    def test_without_it_geonodes_quirks_are_violations(self):
        validator = build_validator(SCHEMA, SCHEMA_URL)
        paths = {e["path"] for e in collect_errors(validator, INSTANCE)}
        self.assertTrue(
            {
                "$.date_type",
                "$.maintenance_frequency",
                "$.related_identifier[0].resource_type_general",
            }
            <= paths
        )

    def test_a_required_null_stays_a_violation(self):
        instance = dict(INSTANCE, category=None)
        self.assertEqual([e["path"] for e in self._errors(instance)], ["$.category"])

    def test_a_nested_required_null_stays_a_violation(self):
        instance = dict(INSTANCE, related_identifier=[{"related_identifier": None}])
        self.assertEqual(
            [e["path"] for e in self._errors(instance)],
            ["$.related_identifier[0].related_identifier"],
        )

    def test_the_input_is_not_modified(self):
        instance = deepcopy(INSTANCE)
        for_validation(SCHEMA, instance)
        self.assertEqual(instance, INSTANCE)


class TestFlattenErrors(unittest.TestCase):
    def test_nested_errors(self):
        errors = {
            "__errors": ["general failure"],
            "contacts": {"owner": {"__errors": ["unknown user", "inactive"]}},
            "title": {"__errors": ["too long"]},
        }
        self.assertEqual(
            flatten_errors(errors),
            [
                ("<root>", "general failure"),
                ("contacts.owner", "unknown user"),
                ("contacts.owner", "inactive"),
                ("title", "too long"),
            ],
        )

    def test_no_errors(self):
        self.assertEqual(flatten_errors({}), [])
        self.assertEqual(flatten_errors(None), [])


if __name__ == "__main__":
    unittest.main()
