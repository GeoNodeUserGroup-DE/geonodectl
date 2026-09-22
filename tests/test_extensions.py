"""The extension mechanism from issue #133.

Extensions are faked by patching the entry point lookup, everything else runs
the way an installed extension package would: through `geonodectl()` for the
cmdline and through `get_handler()` for library mode.
"""

import contextlib
import io
import json
import os
import unittest
from unittest.mock import MagicMock, patch

from geonoderest import extensions
from geonoderest.apiconf import GeonodeApiConf
from geonoderest.cliutils import CMD_METHOD_KEY, VERB_FUNC_KEY
from geonoderest.datasets import GeonodeDatasetsHandler
from geonoderest.exceptions import GeonodeUsageError, UnknownCommandError
from geonoderest.exitcodes import EXIT_FAILED, EXIT_OK, EXIT_USAGE
from geonoderest.extensions import (
    EXTENSION_API_VERSION,
    CommandSpec,
    GeonodectlExtension,
    HandlerOverride,
    VerbSpec,
    build_registry,
    get_handler,
    list_extensions,
)
from geonoderest.geonodectl import build_parser, builtin_commands, geonodectl
from geonoderest.geoserver import GeonodeGeoServerStyleHandler
from geonoderest.maps import GeonodeMapsHandler
from geonoderest.tkeywords import GeonodeThesauriKeywordsRequestHandler

ENV = {
    "GEONODE_API_URL": "https://example.org/api/v2/",
    "GEONODE_API_BASIC_AUTH": "dXNlcjpwYXNz",
}
CONF = GeonodeApiConf(
    url=ENV["GEONODE_API_URL"], auth_basic=ENV["GEONODE_API_BASIC_AUTH"], verify=True
)


def _run(*argv):
    """run geonodectl with the given argv and return its exit code

    ``geonodectl()`` calls ``logging.basicConfig(force=True)``, which would rip
    out the handler ``assertLogs`` installs, so it is stubbed out here.
    """
    with patch("sys.argv", ["geonodectl", *argv]), patch("logging.basicConfig"):
        return geonodectl()


def _run_capturing(*argv):
    """run geonodectl, return its exit code and what it printed"""
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = _run(*argv)
    return code, out.getvalue()


class FakeHandler:
    """handler of the fake `hello` command, remembers how it was called"""

    calls: list = []

    def __init__(self, env):
        self.env = env

    def cmd_greet(self, exit_code=EXIT_OK, **kwargs):
        FakeHandler.calls.append((self.env, kwargs))
        return exit_code


def _build_hello_parser(parser):
    subparsers = parser.add_subparsers(dest="subcommand", required=True)
    greet = subparsers.add_parser("greet", help="greet someone")
    greet.add_argument("--exit-code", dest="exit_code", type=int, default=EXIT_OK)
    return subparsers


def hello_command(**overrides) -> CommandSpec:
    kwargs = dict(
        name="hello",
        help="hello commands",
        build_parser=_build_hello_parser,
        handler_factory=FakeHandler,
    )
    kwargs.update(overrides)
    return CommandSpec(**kwargs)


class FakeExtension(GeonodectlExtension):
    def __init__(self, commands=(), verbs=(), overrides=()):
        self._commands = list(commands)
        self._verbs = list(verbs)
        self._overrides = list(overrides)

    def commands(self):
        return self._commands

    def verbs(self):
        return self._verbs

    def handler_overrides(self):
        return self._overrides


class ZalfThesauriKeywordsHandler(GeonodeThesauriKeywordsRequestHandler):
    def cmd_list(self, **kwargs):
        # a code the built-in never returns for a list, to tell them apart
        return EXIT_FAILED


def _entry_point(name, obj=None, error=None):
    """an installed extension as importlib.metadata reports it"""
    ep = MagicMock()
    ep.name = name
    ep.dist.name = f"geonodectl-{name}"
    ep.dist.version = "1.0.0"
    if error is not None:
        ep.load.side_effect = error
    else:
        ep.load.return_value = obj
    return ep


class ExtensionTestCase(unittest.TestCase):
    def setUp(self):
        extensions._loaded_extensions = None
        self.addCleanup(setattr, extensions, "_loaded_extensions", None)
        FakeHandler.calls = []

    def install(self, *entry_points):
        patcher = patch(
            "geonoderest.extensions.entry_points", return_value=list(entry_points)
        )
        patcher.start()
        self.addCleanup(patcher.stop)


class TestNewCommand(ExtensionTestCase):
    def test_listed_in_help(self):
        self.install(_entry_point("fake", FakeExtension(commands=[hello_command()])))
        out = io.StringIO()
        with contextlib.redirect_stdout(out), self.assertRaises(SystemExit) as cm:
            _run("--help")
        self.assertEqual(cm.exception.code, 0)
        self.assertIn("hello commands", out.getvalue())

    @patch.dict(os.environ, ENV, clear=True)
    def test_dispatches_to_the_cmd_method_and_passes_the_exit_code_on(self):
        self.install(_entry_point("fake", FakeExtension(commands=[hello_command()])))
        code = _run("hello", "greet", "--exit-code", str(EXIT_FAILED))
        self.assertEqual(code, EXIT_FAILED)
        env, kwargs = FakeHandler.calls[0]
        self.assertEqual(env.url, ENV["GEONODE_API_URL"])
        self.assertEqual(kwargs["subcommand"], "greet")
        self.assertNotIn(CMD_METHOD_KEY, kwargs)
        self.assertNotIn(VERB_FUNC_KEY, kwargs)

    @patch.dict(os.environ, {}, clear=True)
    def test_needs_the_geonode_settings_by_default(self):
        self.install(_entry_point("fake", FakeExtension(commands=[hello_command()])))
        with self.assertLogs(level="ERROR"):
            self.assertEqual(_run("hello", "greet"), EXIT_USAGE)
        self.assertEqual(FakeHandler.calls, [])

    @patch.dict(os.environ, {}, clear=True)
    def test_requires_env_false_runs_without_geonode_settings(self):
        command = hello_command(requires_env=False)
        self.install(_entry_point("fake", FakeExtension(commands=[command])))
        self.assertEqual(_run("hello", "greet"), EXIT_OK)
        self.assertIsNone(FakeHandler.calls[0][0])

    def test_entry_point_may_refer_to_the_extension_class(self):
        class ClassExtension(GeonodectlExtension):
            def commands(self):
                return [hello_command()]

        self.install(_entry_point("fake", ClassExtension))
        self.assertIsInstance(get_handler("hello", CONF), FakeHandler)


class TestVerbOnExistingCommand(ExtensionTestCase):
    @patch.dict(os.environ, ENV, clear=True)
    def test_verb_gets_the_handler_of_the_extended_command(self):
        seen = []

        def export(handler, pk, **kwargs):
            seen.append((handler, pk, kwargs))
            return EXIT_FAILED

        verb = VerbSpec(
            command="ds",
            name="export",
            help="export a dataset",
            func=export,
            build_parser=lambda parser: parser.add_argument(dest="pk", type=int),
        )
        self.install(_entry_point("fake", FakeExtension(verbs=[verb])))
        self.assertEqual(_run("dataset", "export", "7"), EXIT_FAILED)
        handler, pk, kwargs = seen[0]
        self.assertIsInstance(handler, GeonodeDatasetsHandler)
        self.assertEqual(pk, 7)
        self.assertNotIn(VERB_FUNC_KEY, kwargs)

    @patch.dict(os.environ, ENV, clear=True)
    @patch.object(GeonodeDatasetsHandler, "cmd_list", return_value=EXIT_OK)
    def test_verb_clashing_with_a_builtin_verb_is_skipped(self, mock_cmd_list):
        func = MagicMock(return_value=EXIT_FAILED)
        verb = VerbSpec(command="dataset", name="list", func=func)
        self.install(_entry_point("fake", FakeExtension(verbs=[verb])))
        with self.assertLogs(level="WARNING"):
            self.assertEqual(_run("dataset", "list"), EXIT_OK)
        mock_cmd_list.assert_called_once()
        func.assert_not_called()

    @patch.dict(os.environ, ENV, clear=True)
    @patch.object(GeonodeDatasetsHandler, "cmd_list", return_value=EXIT_OK)
    def test_verb_for_a_missing_command_is_skipped(self, _):
        verb = VerbSpec(command="nope", name="export", func=MagicMock())
        self.install(_entry_point("fake", FakeExtension(verbs=[verb])))
        with self.assertLogs(level="WARNING"):
            self.assertEqual(_run("dataset", "list"), EXIT_OK)


class TestHandlerOverride(ExtensionTestCase):
    @patch.dict(os.environ, ENV, clear=True)
    def test_subclass_takes_over_the_command(self):
        override = HandlerOverride("tkeywords", ZalfThesauriKeywordsHandler)
        self.install(_entry_point("fake", FakeExtension(overrides=[override])))
        self.assertEqual(_run("tkeywords", "list"), EXIT_FAILED)
        self.assertIsInstance(
            get_handler("tkeywords", CONF), ZalfThesauriKeywordsHandler
        )

    def test_unrelated_class_is_rejected(self):
        override = HandlerOverride("tkeywords", FakeHandler)
        self.install(_entry_point("fake", FakeExtension(overrides=[override])))
        with self.assertLogs(level="WARNING"):
            handler = get_handler("tkeywords", CONF)
        self.assertIs(type(handler), GeonodeThesauriKeywordsRequestHandler)

    def test_command_built_by_a_factory_function_cannot_be_overridden(self):
        override = HandlerOverride("geoserver", GeonodeGeoServerStyleHandler)
        self.install(_entry_point("fake", FakeExtension(overrides=[override])))
        with self.assertLogs(level="WARNING"):
            registry = build_registry(builtin_commands())
        self.assertIsNone(registry.resolve("geoserver").overridden_by)

    def test_second_override_of_a_command_is_ignored(self):
        class OtherHandler(GeonodeThesauriKeywordsRequestHandler):
            pass

        self.install(
            _entry_point(
                "a",
                FakeExtension(
                    overrides=[
                        HandlerOverride("tkeywords", ZalfThesauriKeywordsHandler)
                    ]
                ),
            ),
            _entry_point(
                "b",
                FakeExtension(overrides=[HandlerOverride("tkeywords", OtherHandler)]),
            ),
        )
        with self.assertLogs(level="WARNING"):
            handler = get_handler("tkeywords", CONF)
        self.assertIs(type(handler), ZalfThesauriKeywordsHandler)


class TestBrokenExtensionsNeverBreakTheCore(ExtensionTestCase):
    @patch.dict(os.environ, ENV, clear=True)
    @patch.object(GeonodeDatasetsHandler, "cmd_list", return_value=EXIT_OK)
    def test_extension_failing_to_import(self, _):
        self.install(_entry_point("broken", error=ImportError("no module named x")))
        with self.assertLogs(level="WARNING") as logs:
            self.assertEqual(_run("dataset", "list"), EXIT_OK)
        self.assertIn("broken", "\n".join(logs.output))
        self.assertIn("could not be loaded", list_extensions()[0].error)

    def test_extension_for_another_api_version(self):
        ext = FakeExtension(commands=[hello_command()])
        ext.api_version = EXTENSION_API_VERSION + 1
        self.install(_entry_point("future", ext))
        with self.assertLogs(level="WARNING"), self.assertRaises(UnknownCommandError):
            get_handler("hello", CONF)

    def test_extension_failing_to_tell_its_commands(self):
        class BrokenExtension(GeonodectlExtension):
            def commands(self):
                raise RuntimeError("boom")

        self.install(_entry_point("fake", BrokenExtension()))
        with self.assertLogs(level="WARNING"):
            installed = list_extensions()
        self.assertIn("boom", installed[0].error)

    def test_failing_parser_builder_is_rolled_back(self):
        def broken_builder(parser):
            parser.add_subparsers(dest="subcommand").add_parser("greet")
            raise RuntimeError("boom")

        command = hello_command(build_parser=broken_builder, aliases=("hi",))
        self.install(_entry_point("fake", FakeExtension(commands=[command])))
        registry = build_registry(builtin_commands())
        with self.assertLogs(level="WARNING"):
            parser = build_parser(registry)

        self.assertIsNone(registry.resolve("hello"))
        self.assertIsNone(registry.resolve("hi"))
        self.assertNotIn("hello", parser.format_help())
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            parser.parse_args(["hi", "greet"])
        self.assertEqual(parser.parse_args(["dataset", "list"]).command, "dataset")


class TestNameCollisions(ExtensionTestCase):
    def test_builtin_keeps_its_name(self):
        command = hello_command(name="dataset")
        self.install(_entry_point("fake", FakeExtension(commands=[command])))
        with self.assertLogs(level="WARNING"):
            self.assertIsInstance(get_handler("dataset", CONF), GeonodeDatasetsHandler)

    def test_builtin_keeps_its_aliases(self):
        command = hello_command(aliases=("ds",))
        self.install(_entry_point("fake", FakeExtension(commands=[command])))
        with self.assertLogs(level="WARNING"), self.assertRaises(UnknownCommandError):
            get_handler("hello", CONF)

    def test_first_extension_by_name_wins(self):
        class OtherHandler(FakeHandler):
            pass

        self.install(
            _entry_point(
                "b",
                FakeExtension(commands=[hello_command(handler_factory=OtherHandler)]),
            ),
            _entry_point("a", FakeExtension(commands=[hello_command()])),
        )
        with self.assertLogs(level="WARNING"):
            handler = get_handler("hello", CONF)
        self.assertIs(type(handler), FakeHandler)


class TestLibraryApi(ExtensionTestCase):
    def test_get_handler_of_a_builtin_by_alias(self):
        self.install()
        handler = get_handler("ds", CONF)
        self.assertIsInstance(handler, GeonodeDatasetsHandler)
        self.assertIs(handler.gn_credentials, CONF)

    def test_get_handler_of_an_extension_command(self):
        self.install(_entry_point("fake", FakeExtension(commands=[hello_command()])))
        self.assertIsInstance(get_handler("hello", CONF), FakeHandler)

    def test_unknown_command_is_a_usage_error(self):
        self.install()
        with self.assertRaises(UnknownCommandError) as cm:
            get_handler("nope", CONF)
        self.assertIsInstance(cm.exception, GeonodeUsageError)

    def test_list_extensions(self):
        self.install(_entry_point("fake", FakeExtension()))
        [ext] = list_extensions()
        self.assertEqual(
            (ext.name, ext.distribution, ext.version, ext.error),
            ("fake", "geonodectl-fake", "1.0.0", None),
        )


class TestExtensionsCommand(ExtensionTestCase):
    @patch.dict(os.environ, {}, clear=True)
    def test_list_needs_no_geonode_settings(self):
        self.install(
            _entry_point("fake", FakeExtension()),
            _entry_point("broken", error=ImportError("gone")),
        )
        with self.assertLogs(level="WARNING"):
            code, out = _run_capturing("extensions", "list")
        self.assertEqual(code, EXIT_OK)
        self.assertIn("geonodectl-fake", out)
        self.assertIn("loaded", out)
        self.assertIn("gone", out)

    @patch.dict(os.environ, {}, clear=True)
    def test_list_as_json(self):
        self.install(_entry_point("fake", FakeExtension()))
        code, out = _run_capturing("--json", "extensions", "list")
        self.assertEqual(code, EXIT_OK)
        self.assertEqual(json.loads(out)["extensions"][0]["name"], "fake")

    @patch.dict(os.environ, {}, clear=True)
    def test_list_without_extensions(self):
        self.install()
        code, out = _run_capturing("extensions", "list")
        self.assertEqual(code, EXIT_OK)
        self.assertIn("no geonodectl extensions installed", out)


class TestNestedVerbsStillDispatch(ExtensionTestCase):
    """the dispatcher used to special-case these, the leaf parsers route them now"""

    @patch.dict(os.environ, ENV, clear=True)
    @patch.object(GeonodeMapsHandler, "cmd_maplayers_list", return_value=EXIT_FAILED)
    def test_maps_maplayers(self, mock_cmd):
        self.install()
        self.assertEqual(_run("maps", "maplayers", "list", "3"), EXIT_FAILED)
        # a string since #160, a uuid is accepted there as well
        self.assertEqual(mock_cmd.call_args.kwargs["pk"], "3")

    @patch.dict(os.environ, ENV, clear=True)
    @patch.object(GeonodeMapsHandler, "cmd_widgets_describe", return_value=EXIT_OK)
    def test_maps_widgets(self, mock_cmd):
        self.install()
        self.assertEqual(_run("maps", "widgets", "describe", "3", "w1"), EXIT_OK)
        self.assertEqual(mock_cmd.call_args.kwargs["widget_id"], "w1")

    @patch.dict(os.environ, ENV, clear=True)
    @patch.object(GeonodeGeoServerStyleHandler, "from_env")
    def test_geoserver_styles(self, mock_from_env):
        handler = mock_from_env.return_value
        handler.cmd_style_set_default.return_value = EXIT_OK
        self.install()
        code = _run(
            "geoserver", "styles", "set-default", "--layer", "geonode:x", "--style", "s"
        )
        self.assertEqual(code, EXIT_OK)
        handler.cmd_style_set_default.assert_called_once()

    @patch.dict(os.environ, ENV, clear=True)
    def test_geoserver_without_credentials_is_2(self):
        self.install()
        with self.assertLogs(level="ERROR"):
            self.assertEqual(_run("geoserver", "styles", "list"), EXIT_USAGE)


class TestMalformedSpecsAreSkipped(ExtensionTestCase):
    """whatever an extension hands out is checked before it is registered"""

    @patch.dict(os.environ, ENV, clear=True)
    @patch.object(GeonodeDatasetsHandler, "cmd_list", return_value=EXIT_OK)
    def test_malformed_entries_do_not_break_the_core(self, _):
        ext = FakeExtension(
            commands=[None, hello_command()],
            verbs=["not a verb"],
            overrides=[object()],
        )
        self.install(_entry_point("fake", ext))
        with self.assertLogs(level="WARNING") as logs:
            self.assertEqual(_run("dataset", "list"), EXIT_OK)
        messages = "\n".join(logs.output)
        for spec in ("CommandSpec", "VerbSpec", "HandlerOverride"):
            with self.subTest(spec=spec):
                self.assertIn(spec, messages)

    def test_a_valid_command_next_to_a_malformed_one_still_registers(self):
        ext = FakeExtension(commands=[None, hello_command()])
        self.install(_entry_point("fake", ext))
        with self.assertLogs(level="WARNING"):
            self.assertIsInstance(get_handler("hello", CONF), FakeHandler)


class TestOverrideOfAnotherExtensionsCommand(ExtensionTestCase):
    def test_override_applies_whatever_the_load_order(self):
        class ZalfLikeHandler(FakeHandler):
            pass

        # "a" is registered before "b", the extension adding the command
        self.install(
            _entry_point(
                "a",
                FakeExtension(overrides=[HandlerOverride("hello", ZalfLikeHandler)]),
            ),
            _entry_point("b", FakeExtension(commands=[hello_command()])),
        )
        self.assertIs(type(get_handler("hello", CONF)), ZalfLikeHandler)


class TestCommandWithoutVerbs(ExtensionTestCase):
    @patch.dict(os.environ, ENV, clear=True)
    def test_nothing_to_dispatch_to_is_a_usage_error_not_a_traceback(self):
        command = hello_command(build_parser=lambda parser: None)
        self.install(_entry_point("fake", FakeExtension(commands=[command])))
        with self.assertLogs(level="ERROR"):
            self.assertEqual(_run("hello"), EXIT_USAGE)

    @patch.dict(os.environ, ENV, clear=True)
    def test_a_command_naming_its_own_method_runs(self):
        def build_naming_the_method(parser):
            parser.set_defaults(**{CMD_METHOD_KEY: "cmd_greet"})
            return None

        command = hello_command(build_parser=build_naming_the_method)
        self.install(_entry_point("fake", FakeExtension(commands=[command])))
        self.assertEqual(_run("hello"), EXIT_OK)
        self.assertEqual(len(FakeHandler.calls), 1)


if __name__ == "__main__":
    unittest.main()
