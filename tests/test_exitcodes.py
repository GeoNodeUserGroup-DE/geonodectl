"""The exit code contract from issue #151.

The point of the issue is that `$?` has to be readable from a shell script, so
these tests drive `geonodectl()` the way the console script does rather than
calling handlers directly.
"""

import os
<<<<<<< HEAD
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import requests

from geonoderest.datasets import GeonodeDatasetsHandler
from geonoderest.documents import GeonodeDocumentsHandler
from geonoderest.exceptions import (
    GeoNodeRestException,
    GeonodeUsageError,
    MissingArgumentError,
)
from geonoderest.executionrequest import GeonodeExecutionRequestHandler
=======
import unittest
from unittest.mock import patch

from geonoderest.datasets import GeonodeDatasetsHandler
>>>>>>> 8469f2f77f06012b6e93b29a0598a006cb45aca5
from geonoderest.exitcodes import EXIT_FAILED, EXIT_OK, EXIT_USAGE
from geonoderest.geonodectl import __exit_code__, geonodectl
from geonoderest.linkedresources import GeonodeLinkedResourcesHandler
from geonoderest.maps import GeonodeMapsHandler
<<<<<<< HEAD
from geonoderest.users import GeonodeUsersHandler
=======
>>>>>>> 8469f2f77f06012b6e93b29a0598a006cb45aca5

ENV = {
    "GEONODE_API_URL": "https://example.org/api/v2/",
    "GEONODE_API_BASIC_AUTH": "dXNlcjpwYXNz",
}


def _run(*argv):
    """run geonodectl with the given argv and return its exit code

    ``geonodectl()`` calls ``logging.basicConfig(force=True)``, which would rip
    out the handler ``assertLogs`` installs, so it is stubbed out here.
    """
    with patch("sys.argv", ["geonodectl", *argv]), patch("logging.basicConfig"):
        return geonodectl()


class TestExitCodeHelper(unittest.TestCase):
    def test_none_is_success(self):
        """a cmd_* with nothing to report stays exit 0 - backwards compatible"""
        self.assertEqual(__exit_code__(None), EXIT_OK)

    def test_a_returned_code_is_passed_through(self):
        self.assertEqual(__exit_code__(EXIT_FAILED), EXIT_FAILED)
        self.assertEqual(__exit_code__(EXIT_USAGE), EXIT_USAGE)


class TestDispatcherPropagatesExitCodes(unittest.TestCase):
    """end to end: the code a cmd_* returns must reach geonodectl()'s caller"""

    @patch.dict(os.environ, ENV, clear=True)
    @patch.object(GeonodeDatasetsHandler, "http_get")
    def test_describe_success_is_0(self, mock_http_get):
        mock_http_get.return_value = {"dataset": {"pk": 1, "title": "t"}}
        self.assertEqual(_run("dataset", "describe", "1"), EXIT_OK)

    @patch.dict(os.environ, ENV, clear=True)
    @patch.object(GeonodeDatasetsHandler, "http_get", return_value=None)
    def test_describe_404_is_1(self, _):
        """the headline bug: a failed operation used to exit 0"""
        with self.assertLogs(level="ERROR"):
            self.assertEqual(_run("dataset", "describe", "999999"), EXIT_FAILED)

    @patch.dict(os.environ, ENV, clear=True)
    @patch.object(GeonodeDatasetsHandler, "http_delete", return_value=None)
    def test_delete_404_is_1(self, _):
        with self.assertLogs(level="ERROR"):
            self.assertEqual(_run("dataset", "delete", "999999"), EXIT_FAILED)

    @patch.dict(os.environ, ENV, clear=True)
    @patch.object(GeonodeMapsHandler, "http_patch", return_value=None)
    def test_patch_404_is_1(self, _):
        with self.assertLogs(level="ERROR"):
            code = _run("maps", "patch", "999999", "--set", '{"title":"x"}')
        self.assertEqual(code, EXIT_FAILED)

    @patch.dict(os.environ, ENV, clear=True)
    @patch.object(GeonodeDatasetsHandler, "http_get")
    def test_invalid_pk_is_2_not_a_traceback(self, mock_http_get):
        """the second defect in #151: these used to escape as ValueError"""
        for pk in ("abc", "1-2-3", "a-b", "1,a"):
            with self.subTest(pk=pk), self.assertLogs(level="ERROR"):
                self.assertEqual(_run("dataset", "describe", pk), EXIT_USAGE)
        mock_http_get.assert_not_called()

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_env_vars_is_2(self):
        with self.assertLogs(level="ERROR"):
            self.assertEqual(_run("dataset", "list"), EXIT_USAGE)

    @patch.dict(
        os.environ, {**ENV, "GEONODE_API_URL": "https://example.org/"}, clear=True
    )
    def test_malformed_api_url_is_2(self):
        """used to escape as a NameError traceback"""
        with self.assertLogs(level="ERROR"):
            self.assertEqual(_run("dataset", "list"), EXIT_USAGE)


class TestPartialFailureInAPkRange(unittest.TestCase):
    """one failure in a range is enough to report failure (#151)"""

    @patch.dict(os.environ, ENV, clear=True)
    @patch.object(GeonodeDatasetsHandler, "http_get")
    def test_all_succeed_is_0(self, mock_http_get):
        mock_http_get.return_value = {"dataset": {"pk": 1}}
        self.assertEqual(_run("dataset", "describe", "1-3"), EXIT_OK)

    @patch.dict(os.environ, ENV, clear=True)
    @patch.object(GeonodeDatasetsHandler, "http_get")
    def test_one_of_three_fails_is_1(self, mock_http_get):
        mock_http_get.side_effect = [
            {"dataset": {"pk": 1}},
            None,
            {"dataset": {"pk": 3}},
        ]
        with self.assertLogs(level="ERROR"):
            code = _run("dataset", "describe", "1,2,3")
        self.assertEqual(code, EXIT_FAILED)
        # the run still visits every pk rather than stopping at the first failure
        self.assertEqual(mock_http_get.call_count, 3)

    @patch.dict(os.environ, ENV, clear=True)
    @patch.object(GeonodeDatasetsHandler, "http_delete")
    def test_partial_delete_is_1(self, mock_delete):
        mock_delete.side_effect = [{"ok": True}, None]
        with self.assertLogs(level="ERROR"):
            self.assertEqual(_run("dataset", "delete", "1,2"), EXIT_FAILED)


class TestLinkedResourcesEmptyList(unittest.TestCase):
    """an unset shell variable must not pass as a successful no-op (#151)"""

    @patch.dict(os.environ, ENV, clear=True)
    @patch.object(GeonodeLinkedResourcesHandler, "http_post")
    def test_add_with_no_pks_is_2(self, mock_post):
        with self.assertLogs(level="ERROR"):
            self.assertEqual(
                GeonodeLinkedResourcesHandler(env={}).cmd_add(pk=1, linked_to=[]),
                EXIT_USAGE,
            )
        mock_post.assert_not_called()

    @patch.dict(os.environ, ENV, clear=True)
    @patch.object(GeonodeLinkedResourcesHandler, "http_post")
    def test_add_with_linked_to_unset_is_2(self, mock_post):
        """argparse leaves --linked-to as None; len(None) used to traceback"""
        with self.assertLogs(level="ERROR"):
            self.assertEqual(
                GeonodeLinkedResourcesHandler(env={}).cmd_add(pk=1, linked_to=None),
                EXIT_USAGE,
            )
        mock_post.assert_not_called()

    @patch.dict(os.environ, ENV, clear=True)
    @patch.object(GeonodeLinkedResourcesHandler, "http_delete")
    def test_delete_with_linked_to_unset_is_2(self, mock_delete):
        with self.assertLogs(level="ERROR"):
            self.assertEqual(
                GeonodeLinkedResourcesHandler(env={}).cmd_delete(pk=1, linked_to=None),
                EXIT_USAGE,
            )
        mock_delete.assert_not_called()

    @patch.dict(os.environ, ENV, clear=True)
    @patch.object(GeonodeLinkedResourcesHandler, "http_delete")
    def test_delete_with_no_pks_is_2(self, mock_delete):
        with self.assertLogs(level="ERROR"):
            self.assertEqual(
                GeonodeLinkedResourcesHandler(env={}).cmd_delete(pk=1, linked_to=[]),
                EXIT_USAGE,
            )
        mock_delete.assert_not_called()


<<<<<<< HEAD
class TestReviewFindings(unittest.TestCase):
    """regressions found reviewing this change - one case per finding"""

    @patch.dict(os.environ, ENV, clear=True)
    @patch.object(GeonodeUsersHandler, "http_get", return_value={"user": {}})
    @patch.object(GeonodeUsersHandler, "http_delete", return_value={"ok": True})
    def test_users_delete_success_is_0(self, mock_delete, _):
        """users.delete() swallowed its response, so every delete reported failure"""
        self.assertEqual(_run("users", "delete", "5"), EXIT_OK)
        mock_delete.assert_called_once()

    @patch.dict(os.environ, ENV, clear=True)
    @patch.object(GeonodeUsersHandler, "http_get", return_value={"user": {}})
    @patch.object(GeonodeUsersHandler, "http_delete", return_value=None)
    def test_users_delete_failure_is_still_1(self, *_):
        with self.assertLogs(level="ERROR"):
            self.assertEqual(_run("users", "delete", "999999"), EXIT_FAILED)

    @patch.dict(os.environ, ENV, clear=True)
    @patch.object(
        GeonodeDatasetsHandler, "http_get", side_effect=GeoNodeRestException("no route")
    )
    def test_unreachable_api_is_1_not_a_traceback(self, _):
        """network_exception_handling raises; nothing used to catch it"""
        with self.assertLogs(level="ERROR"):
            self.assertEqual(_run("dataset", "list"), EXIT_FAILED)

    @patch.object(GeonodeExecutionRequestHandler, "http_get", return_value=None)
    def test_executionrequest_describe_404_is_1(self, _):
        """get() dereferenced None, so the cmd layer's guard was dead code"""
        with self.assertLogs(level="ERROR"):
            code = GeonodeExecutionRequestHandler(env={}).cmd_describe(exec_id="bad")
        self.assertEqual(code, EXIT_FAILED)

    @patch.dict(os.environ, ENV, clear=True)
    @patch.object(GeonodeDatasetsHandler, "http_delete")
    def test_reversed_pk_range_is_2_not_a_silent_success(self, mock_delete):
        """`delete 5-1` yielded an empty range: nothing done, exit 0"""
        with self.assertLogs(level="ERROR"):
            self.assertEqual(_run("dataset", "delete", "5-1"), EXIT_USAGE)
        mock_delete.assert_not_called()

    @patch.object(GeonodeMapsHandler, "http_post")
    @patch.object(GeonodeMapsHandler, "__build_blob_data__")
    @patch("geonoderest.datasets.GeonodeDatasetsHandler.get", return_value=None)
    def test_maps_create_with_unknown_maplayer_is_1(self, _, mock_blob, mock_post):
        """a missing dataset used to reach __build_maplayer_pair__ as None"""
        mock_blob.return_value = {"map": {"layers": []}, "maplayers": []}
        with self.assertLogs(level="ERROR"):
            code = GeonodeMapsHandler(env={}).cmd_create(
                title="t", maplayers=[999999], json=False
            )
        self.assertEqual(code, EXIT_FAILED)
        # the map must not be created at all rather than created without the layer
        mock_post.assert_not_called()

    def test_upload_of_a_directory_is_2(self):
        """only FileNotFoundError was caught, so a directory tracebacked"""
        with tempfile.TemporaryDirectory() as d, self.assertLogs(level="ERROR"):
            code = GeonodeDocumentsHandler(env={}).cmd_upload(
                file_path=Path(d), json=False
            )
        self.assertEqual(code, EXIT_USAGE)

    def test_malformed_api_response_is_1_not_2(self):
        """JSONDecodeError is a ValueError; it must not read as a usage error"""
        r = MagicMock()
        r.raise_for_status.return_value = None
        r.json.side_effect = requests.exceptions.JSONDecodeError("x", "<html>", 0)
        r.url, r.text = "https://x/api/v2/datasets/1", "<html>login</html>"
        env = MagicMock(url="https://x/api/v2/", auth_basic="a", verify=True)
        with patch("geonoderest.rest.requests.get", return_value=r):
            with self.assertLogs(level="ERROR"):
                code = GeonodeDatasetsHandler(env=env).cmd_describe(pk="1")
        self.assertEqual(code, EXIT_FAILED)

    def test_missing_username_is_a_usage_error_not_a_bare_value_error(self):
        """the cmd layer catches GeonodeUsageError, deliberately not ValueError"""
        with self.assertRaises(MissingArgumentError):
            GeonodeUsersHandler(env={}).create()
        self.assertTrue(issubclass(MissingArgumentError, GeonodeUsageError))
        self.assertFalse(
            issubclass(requests.exceptions.JSONDecodeError, GeonodeUsageError)
        )


=======
>>>>>>> 8469f2f77f06012b6e93b29a0598a006cb45aca5
class TestLibraryMethodsNeverExit(unittest.TestCase):
    """issue #69: geonoderest is also a library and must not kill its host"""

    def test_no_sys_exit_left_in_library_modules(self):
        """guards the boundary: only the dispatcher may exit the process"""
        import ast
        from pathlib import Path

        import geonoderest

        # geonoderest ships without an __init__.py, so __file__ is None
        pkg = Path(list(geonoderest.__path__)[0])

        def exits(node) -> bool:
            if isinstance(node, ast.Raise):
                exc = node.exc
                if isinstance(exc, ast.Call):
                    exc = exc.func
                return isinstance(exc, ast.Name) and exc.id == "SystemExit"
            if isinstance(node, ast.Call):
                f = node.func
                return (
                    isinstance(f, ast.Attribute)
                    and f.attr == "exit"
                    and isinstance(f.value, ast.Name)
                    and f.value.id == "sys"
                )
            return False

        offenders = []
        for path in sorted(pkg.glob("*.py")):
            # the dispatcher is the one place allowed to exit the process
            if path.name == "geonodectl.py":
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if exits(node):
                    offenders.append(f"{path.name}:{node.lineno}")
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
