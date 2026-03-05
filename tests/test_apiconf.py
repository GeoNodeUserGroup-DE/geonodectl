import os
import unittest
from pathlib import Path
from textwrap import dedent
from unittest.mock import patch

from geonoderest.apiconf import GeonodeApiConf


class TestGeonodeApiConfFromEnvFile(unittest.TestCase):
    def _write_env(self, tmp_path: Path, content: str) -> Path:
        env_file = tmp_path / ".env"
        env_file.write_text(dedent(content))
        return env_file

    def test_all_keys_parsed(self, tmp_path=None):
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            env_file = self._write_env(
                Path(d),
                """
                GEONODE_API_URL=http://example.com/api/v2/
                GEONODE_API_BASIC_AUTH=dGVzdDp0ZXN0
                GEONODE_API_VERIFY=True
                """,
            )
            conf = GeonodeApiConf.from_env_file(env_file)
            self.assertEqual(conf.url, "http://example.com/api/v2/")
            self.assertEqual(conf.auth_basic, "dGVzdDp0ZXN0")
            self.assertTrue(conf.verify)

    def test_verify_false(self):
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            env_file = Path(d) / ".env"
            env_file.write_text(
                "GEONODE_API_URL=http://example.com/api/v2/\n"
                "GEONODE_API_BASIC_AUTH=abc\n"
                "GEONODE_API_VERIFY=False\n"
            )
            conf = GeonodeApiConf.from_env_file(env_file)
            self.assertFalse(conf.verify)

    def test_verify_defaults_to_true_when_missing(self):
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            env_file = Path(d) / ".env"
            env_file.write_text(
                "GEONODE_API_URL=http://example.com/api/v2/\n"
                "GEONODE_API_BASIC_AUTH=abc\n"
            )
            conf = GeonodeApiConf.from_env_file(env_file)
            self.assertTrue(conf.verify)

    def test_comment_lines_ignored(self):
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            env_file = Path(d) / ".env"
            env_file.write_text(
                "# This is a comment\n"
                "GEONODE_API_URL=http://example.com/api/v2/\n"
                "GEONODE_API_BASIC_AUTH=abc\n"
            )
            conf = GeonodeApiConf.from_env_file(env_file)
            self.assertEqual(conf.url, "http://example.com/api/v2/")

    def test_value_with_equals_sign_parsed_correctly(self):
        """Values that contain '=' must not be split on the inner '='."""
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            env_file = Path(d) / ".env"
            env_file.write_text(
                "GEONODE_API_URL=http://example.com/api/v2/\n"
                "GEONODE_API_BASIC_AUTH=dGVzdDp0ZXN0==\n"
            )
            conf = GeonodeApiConf.from_env_file(env_file)
            self.assertEqual(conf.auth_basic, "dGVzdDp0ZXN0==")

    def test_values_are_stripped_of_whitespace(self):
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            env_file = Path(d) / ".env"
            env_file.write_text(
                "GEONODE_API_URL=http://example.com/api/v2/  \n"
                "GEONODE_API_BASIC_AUTH=abc  \n"
            )
            conf = GeonodeApiConf.from_env_file(env_file)
            self.assertEqual(conf.url, "http://example.com/api/v2/")
            self.assertEqual(conf.auth_basic, "abc")

    def test_missing_url_raises_systemexit(self):
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            env_file = Path(d) / ".env"
            env_file.write_text("GEONODE_API_BASIC_AUTH=abc\n")
            with self.assertRaises(SystemExit) as cm:
                GeonodeApiConf.from_env_file(env_file)
            self.assertIn("GEONODE_API_URL", str(cm.exception))

    def test_missing_auth_raises_systemexit(self):
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            env_file = Path(d) / ".env"
            env_file.write_text("GEONODE_API_URL=http://example.com/api/v2/\n")
            with self.assertRaises(SystemExit) as cm:
                GeonodeApiConf.from_env_file(env_file)
            self.assertIn("GEONODE_API_BASIC_AUTH", str(cm.exception))

    def test_both_missing_reports_both_keys(self):
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            env_file = Path(d) / ".env"
            env_file.write_text("# empty\n")
            with self.assertRaises(SystemExit) as cm:
                GeonodeApiConf.from_env_file(env_file)
            msg = str(cm.exception)
            self.assertIn("GEONODE_API_URL", msg)
            self.assertIn("GEONODE_API_BASIC_AUTH", msg)


class TestGeonodeApiConfFromEnvVars(unittest.TestCase):
    def test_reads_env_vars(self):
        with patch.dict(
            os.environ,
            {
                "GEONODE_API_URL": "http://example.com/api/v2/",
                "GEONODE_API_BASIC_AUTH": "dGVzdDp0ZXN0",
                "GEONODE_API_VERIFY": "True",
            },
        ):
            conf = GeonodeApiConf.from_env_vars()
            self.assertEqual(conf.url, "http://example.com/api/v2/")
            self.assertEqual(conf.auth_basic, "dGVzdDp0ZXN0")
            self.assertTrue(conf.verify)

    def test_verify_false_from_env(self):
        with patch.dict(
            os.environ,
            {
                "GEONODE_API_URL": "http://example.com/api/v2/",
                "GEONODE_API_BASIC_AUTH": "abc",
                "GEONODE_API_VERIFY": "False",
            },
        ):
            conf = GeonodeApiConf.from_env_vars()
            self.assertFalse(conf.verify)

    def test_missing_url_raises_systemexit(self):
        env = {"GEONODE_API_BASIC_AUTH": "abc"}
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaises(SystemExit):
                GeonodeApiConf.from_env_vars()

    def test_missing_auth_raises_systemexit(self):
        env = {"GEONODE_API_URL": "http://example.com/api/v2/"}
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaises(SystemExit):
                GeonodeApiConf.from_env_vars()

    def test_get_geonode_base_url(self):
        conf = GeonodeApiConf(
            url="http://example.com/api/v2/",
            auth_basic="abc",
            verify=True,
        )
        # url[:-8] strips 'api/v2/' (7 chars + leading '/') — no trailing slash
        self.assertEqual(conf.get_geonode_base_url(), "http://example.com")


if __name__ == "__main__":
    unittest.main()
